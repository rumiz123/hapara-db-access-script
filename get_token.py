# token_logger.py

from mitmproxy import http, ctx
import json, time, webbrowser
from threading import Timer


class TokenLogger:
    TARGET_URL = "https://api.hapara.com/auth-service/oauth/token?grant_type=refresh_token"
    BROWSER_URL = "https://app.hapara.com/student/login"
    LAUNCH_DELAY = 1  # seconds before launching browser

    def load(self, loader):
        loader.add_option("outfile", str, "captures.jsonl", "Output file (JSON Lines).")
        loader.add_option("capture_bodies", bool, True, "Whether to log request/response bodies.")
        loader.add_option("max_body_kb", int, 64, "Max body size to store (KB).")

    def configure(self, updated):
        self.outfile = ctx.options.outfile
        self.capture_bodies = ctx.options.capture_bodies
        self.max_bytes = max(0, int(ctx.options.max_body_kb)) * 1024
        self._fh = open(self.outfile, "ab")

        # Schedule browser launch after a short delay
        Timer(self.LAUNCH_DELAY, self.launch_browser).start()

        ctx.log.info(f"[token_logger] Logging ALL content from {self.TARGET_URL}")
        ctx.log.info(f"[token_logger] Will open {self.BROWSER_URL} in browser")

    def launch_browser(self):
        """Open the target URL in the default web browser"""
        try:
            webbrowser.open_new_tab(self.BROWSER_URL)
            ctx.log.info(f"[token_logger] Launched browser to {self.BROWSER_URL}")
        except Exception as e:
            ctx.log.error(f"[token_logger] Failed to launch browser: {str(e)}")

    def response(self, flow: http.HTTPFlow):
        if not flow.request.pretty_url.startswith(self.TARGET_URL):
            return  # ignore everything else

        now = time.time()
        req, resp = flow.request, flow.response

        entry = {
            "ts": now,
            "method": req.method,
            "url": req.pretty_url,
            "status_code": resp.status_code,
            "request_headers": list(req.headers.items(multi=True)),
            "response_headers": list(resp.headers.items(multi=True)),
            "request_bytes": len(req.raw_content or b""),
            "response_bytes": len(resp.raw_content or b""),
        }

        if self.capture_bodies and self.max_bytes > 0:
            entry["request_body"] = (req.raw_content or b"")[:self.max_bytes].decode("utf-8", errors="replace")
            entry["response_body"] = (resp.raw_content or b"")[:self.max_bytes].decode("utf-8", errors="replace")

        line = (json.dumps(entry, ensure_ascii=False) + "\n").encode("utf-8")
        self._fh.write(line)
        self._fh.flush()

    def done(self):
        try:
            self._fh.close()
        except Exception:
            pass


addons = [TokenLogger()]