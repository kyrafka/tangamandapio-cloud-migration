(() => {
  "use strict";

  const NativePeerConnection = window.RTCPeerConnection;
  if (
    typeof NativePeerConnection !== "function" ||
    NativePeerConnection.__tangamaIceConfigWrapped
  ) {
    return;
  }

  const REQUEST_TIMEOUT_MS = 3000;
  const ICE_CONFIG_PATH = "/api/voice/ice-config";

  function sanitizeIceServers(servers) {
    if (!Array.isArray(servers)) return [];
    return servers.flatMap((server) => {
      if (!server || typeof server !== "object") return [];
      const urls = Array.isArray(server.urls) ? server.urls : [server.urls];
      if (
        urls.length === 0 ||
        urls.some(
          (url) =>
            typeof url !== "string" || !/^(stun|stuns|turn|turns):/i.test(url),
        )
      ) {
        return [];
      }

      const safeServer = { urls: Array.isArray(server.urls) ? urls : urls[0] };
      if (
        typeof server.username === "string" &&
        typeof server.credential === "string" &&
        server.username.length > 0 &&
        server.credential.length > 0
      ) {
        safeServer.username = server.username;
        safeServer.credential = server.credential;
        if (server.credentialType === "password") {
          safeServer.credentialType = "password";
        }
      }
      return [safeServer];
    });
  }

  class ConfiguredPeerConnection extends NativePeerConnection {
    constructor(configuration = {}, constraints) {
      super(configuration, constraints);
      this.__tangamaIceConfigReady = this.loadIceConfiguration(configuration);
    }

    async loadIceConfiguration(originalConfiguration) {
      const controller = new AbortController();
      const timeout = window.setTimeout(
        () => controller.abort(),
        REQUEST_TIMEOUT_MS,
      );
      try {
        const response = await window.fetch(ICE_CONFIG_PATH, {
          credentials: "same-origin",
          cache: "no-store",
          headers: { Accept: "application/json" },
          signal: controller.signal,
        });
        if (!response.ok) return;
        const payload = await response.json();
        const iceServers = sanitizeIceServers(payload?.ice_servers);
        if (iceServers.length === 0) return;

        // This runs before SDP negotiation, so the relay can be used from the
        // initial offer/answer instead of trying to retrofit a live ICE session.
        this.setConfiguration({ ...originalConfiguration, iceServers });
      } catch {
        // Keep the bundled public STUN server as a bounded fallback. Never log
        // the API response because TURN credentials are short-lived secrets.
      } finally {
        window.clearTimeout(timeout);
      }
    }

    async setRemoteDescription(description) {
      await this.__tangamaIceConfigReady;
      return super.setRemoteDescription(description);
    }

    async createOffer(options) {
      await this.__tangamaIceConfigReady;
      return super.createOffer(options);
    }

    async createAnswer(options) {
      await this.__tangamaIceConfigReady;
      return super.createAnswer(options);
    }
  }

  Object.defineProperty(ConfiguredPeerConnection, "__tangamaIceConfigWrapped", {
    value: true,
  });
  window.RTCPeerConnection = ConfiguredPeerConnection;
})();
