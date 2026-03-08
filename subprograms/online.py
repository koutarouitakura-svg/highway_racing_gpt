from .common import math, json, queue, threading, _time, SUPABASE_URL, SUPABASE_ANON_KEY, _HAS_WS, _ws, _asyncio

class OnlineClient:
    """
    Supabase Realtime Broadcast を使ったオンラインクライアント。
    設計原則: ws.recv() を呼ぶのは _loop() だけ（同時recv競合を防ぐ）
    - phx_joinのackは asyncio.Event で _loop() → _handshake_done に通知
    - broadcastメッセージは recv_q (dict) に積む
    - 送信は send_q (JSON文字列) 経由で _loop() が行う
    """
    _WS_TEMPLATE = "{base}/realtime/v1/websocket?apikey={key}&vsn=1.0.0"

    def __init__(self, url, room_id, player_id):
        self.room_id   = room_id
        self.player_id = player_id
        self.send_q    = queue.Queue(maxsize=8)
        self.recv_q    = queue.Queue()
        self.connected = False
        self.error     = ""
        self._last_send_t  = 0.0
        self.SEND_INTERVAL = 1.0 / 20   # 20Hz

        base = SUPABASE_URL.replace("https://", "wss://").replace("http://", "ws://")
        self._ws_url  = self._WS_TEMPLATE.format(base=base, key=SUPABASE_ANON_KEY)
        self._channel = f"realtime:highway_racer:{room_id}"

        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        _asyncio.run(self._main())

    async def _main(self):
        backoff = 1.0
        while True:
            try:
                async with _ws.connect(
                    self._ws_url,
                    open_timeout=15,
                    ping_interval=25,
                    ping_timeout=10,
                    extra_headers={"apikey": SUPABASE_ANON_KEY},
                ) as ws:
                    self.error = ""
                    backoff    = 1.0
                    await self._loop(ws)
            except Exception as e:
                self.connected = False
                self.error = str(e)
                print(f"[OnlineClient] 切断/エラー: {e}")
                await _asyncio.sleep(min(backoff, 10.0))
                backoff *= 1.5

    async def _loop(self, ws):
        """
        受信・送信・heartbeatを1つのコルーチンで管理。
        ws.recv() を呼ぶのはここだけ → concurrent recv エラーを完全回避。
        """
        # 1. phx_join 送信
        await ws.send(json.dumps({
            "topic":   self._channel,
            "event":   "phx_join",
            "payload": {
                "config": {
                    "broadcast": {"self": False, "ack": False},
                    "presence":  {"key": ""},
                }
            },
            "ref": "1"
        }))
        print(f"[OnlineClient] phx_join 送信: {self._channel}")

        join_ok      = False
        heartbeat_t  = _asyncio.get_running_loop().time()
        hb_ref       = 1

        while True:
            # ── 送信キューを全部捌く（ノンブロッキング）──
            while not self.send_q.empty():
                try:
                    payload_str = self.send_q.get_nowait()
                    inner = json.loads(payload_str)
                    msg = {
                        "topic":   self._channel,
                        "event":   "broadcast",
                        "payload": {"event": "game", "payload": inner},
                        "ref":     None,
                    }
                    await ws.send(json.dumps(msg))
                except queue.Empty:
                    break
                except Exception as e:
                    print(f"[OnlineClient] 送信エラー: {e}")
                    return

            # ── heartbeat (20秒ごと) ──
            now = _asyncio.get_running_loop().time()
            if now - heartbeat_t >= 20.0:
                hb_ref += 1
                heartbeat_t = now
                try:
                    await ws.send(json.dumps({
                        "topic": "phoenix", "event": "heartbeat",
                        "payload": {}, "ref": str(hb_ref)
                    }))
                except Exception as e:
                    print(f"[OnlineClient] heartbeatエラー: {e}")
                    return

            # ── 受信（タイムアウト付き: 送信・heartbeatを止めないため短く）──
            try:
                raw = await _asyncio.wait_for(ws.recv(), timeout=0.05)
            except _asyncio.TimeoutError:
                continue
            except Exception as e:
                print(f"[OnlineClient] 受信エラー: {e}")
                return

            try:
                msg = json.loads(raw)
            except Exception:
                continue

            ev = msg.get("event", "")

            # phx_join の ack → connected=True にする
            if ev == "phx_reply" and not join_ok:
                status = msg.get("payload", {}).get("status", "")
                if status == "ok":
                    join_ok = True
                    self.connected = True
                    print(f"[OnlineClient] チャンネル参加成功: {self._channel}")
                else:
                    print(f"[OnlineClient] phx_join 失敗: {msg}")
                    return
                continue

            # broadcast メッセージをゲームループへ渡す
            if ev == "broadcast":
                inner = msg.get("payload", {}).get("payload")
                if isinstance(inner, dict):
                    if self.recv_q.qsize() > 20:
                        try: self.recv_q.get_nowait()
                        except: pass
                    self.recv_q.put(inner)

    # ── ゲームループから呼ぶ公開メソッド ──────────────────────────────────

    def send(self, data: dict):
        """スロットリング付き送信（20Hz上限）。位置データ等に使用。"""
        now = _time.monotonic()
        if now - self._last_send_t < self.SEND_INTERVAL:
            return
        self._last_send_t = now
        self._enqueue(data, now)

    def send_priority(self, data: dict):
        """スロットリングなし送信。start/join/settings等の制御メッセージに使用。"""
        now = _time.monotonic()
        self._last_send_t = now
        self._enqueue(data, now)

    def _enqueue(self, data: dict, now: float):
        data["t"] = now
        payload = json.dumps(data)
        if self.send_q.full():
            try: self.send_q.get_nowait()
            except: pass
        try: self.send_q.put_nowait(payload)
        except: pass

    def recv_all(self) -> list:
        """受信キューを全て取り出して返す（要素はdict）。"""
        out = []
        while not self.recv_q.empty():
            try:
                item = self.recv_q.get_nowait()
                if isinstance(item, dict):
                    out.append(item)
            except: pass
        return out


# ── ピア補間エンジン ──────────────────────────────────────────────────────────
class PeerInterpolator:
    """
    受信パケット間を滑らかに補間して相手の位置ガタつきを除去する。

    アルゴリズム:
      - 受信パケットをスナップショットバッファ(最大8件)に蓄積
      - 描画時は「現在時刻 - INTERP_DELAY だけ前」のスナップショットを
        前後2点の線形補間で求める（バッファリング補間）
      - バッファが空・遅延オーバー時はデッドレコニングにフォールバック

    これにより:
      - 受信間隔のバラつき(ジッター)を吸収
      - 急なジャンプを消す
      - ラグは INTERP_DELAY(100ms)増えるが滑らかになる
    """
    INTERP_DELAY = 0.10   # バッファリング遅延(秒)。小さいほどリアルタイム/ガタつく
    MAX_SNAPS    = 8      # スナップショットバッファサイズ

    def __init__(self):
        self.snaps  = []   # [(recv_time, {x,y,angle,vx,vy,vel,...}), ...]
        self.render = {}   # 補間済みの描画用状態

    def push(self, snap: dict, recv_time: float):
        """新しいスナップショットを追加"""
        # タイムスタンプが古いパケットは無視
        if self.snaps and snap.get("t", 0) <= self.snaps[-1][1].get("t", 0):
            return
        self.snaps.append((recv_time, snap))
        if len(self.snaps) > self.MAX_SNAPS:
            self.snaps.pop(0)

    def update(self, now: float) -> dict:
        """
        now時刻でのレンダリング用状態を計算して返す。
        バッファリング補間 → デッドレコニングの順でフォールバック。
        """
        target_t = now - self.INTERP_DELAY

        # ── ① バッファリング補間 ──
        if len(self.snaps) >= 2:
            # target_t を挟む2スナップショットを探す
            for i in range(len(self.snaps) - 1):
                t0, s0 = self.snaps[i]
                t1, s1 = self.snaps[i + 1]
                if t0 <= target_t <= t1:
                    alpha = (target_t - t0) / max(t1 - t0, 1e-6)
                    alpha = max(0.0, min(1.0, alpha))
                    self.render = self._lerp(s0, s1, alpha)
                    return self.render

        # ── ② デッドレコニング（最新スナップから外挿）──
        if self.snaps:
            _, s = self.snaps[-1]
            dt = min(now - self.snaps[-1][0], 0.25)
            vx = s.get("vx", math.cos(s.get("angle", 0)) * s.get("vel", 0))
            vy = s.get("vy", math.sin(s.get("angle", 0)) * s.get("vel", 0))
            pred = dict(s)
            pred["x"] = s.get("x", 0) + vx * dt * 30
            pred["y"] = s.get("y", 0) + vy * dt * 30
            # render との差が大きすぎる場合は急に補正せず lerp で寄せる
            if self.render:
                err = math.hypot(pred["x"] - self.render.get("x", pred["x"]),
                                 pred["y"] - self.render.get("y", pred["y"]))
                a = min(0.15, err * 0.03) if err < 5.0 else 0.4
                self.render["x"]     = self.render.get("x", pred["x"])     + (pred["x"]     - self.render.get("x",     pred["x"]))     * a
                self.render["y"]     = self.render.get("y", pred["y"])     + (pred["y"]     - self.render.get("y",     pred["y"]))     * a
                self.render["angle"] = self.render.get("angle", pred["angle"]) + (pred["angle"] - self.render.get("angle", pred["angle"])) * 0.2
                self.render["vel"]   = pred.get("vel", 0)
                self.render["vx"]    = vx
                self.render["vy"]    = vy
            else:
                self.render = pred
            return self.render

        return self.render  # スナップなし → 前回値をそのまま返す

    @staticmethod
    def _lerp(a: dict, b: dict, t: float) -> dict:
        """2スナップショット間を線形補間"""
        out = dict(b)
        for k in ("x", "y", "vel", "vx", "vy"):
            va = a.get(k, 0.0)
            vb = b.get(k, 0.0)
            out[k] = va + (vb - va) * t
        # 角度は最短経路で補間（±π折り返し対応）
        aa = a.get("angle", 0.0)
        ab = b.get("angle", 0.0)
        diff = (ab - aa + math.pi) % (2 * math.pi) - math.pi
        out["angle"] = aa + diff * t
        return out
