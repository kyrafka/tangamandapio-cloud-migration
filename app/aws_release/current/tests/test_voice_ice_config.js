const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const assetPath = path.join(
  __dirname,
  "..",
  "static",
  "assets",
  "voice-ice-config-20261016.js",
);
const indexPath = path.join(__dirname, "..", "static", "index.html");
const shimSource = readFileSync(assetPath, "utf8");

function loadPeerConnection(fetchImplementation) {
  class FakePeerConnection {
    constructor(configuration, constraints) {
      this.configuration = configuration;
      this.constraints = constraints;
      this.calls = [];
    }

    setConfiguration(configuration) {
      this.configuration = configuration;
      this.calls.push("setConfiguration");
    }

    async setRemoteDescription(description) {
      this.calls.push("setRemoteDescription");
      return description;
    }

    async createOffer(options) {
      this.calls.push("createOffer");
      return { type: "offer", options };
    }

    async createAnswer(options) {
      this.calls.push("createAnswer");
      return { type: "answer", options };
    }
  }

  const context = vm.createContext({
    AbortController,
    RTCPeerConnection: FakePeerConnection,
    clearTimeout,
    fetch: fetchImplementation,
    setTimeout,
  });
  context.window = context;
  vm.runInContext(shimSource, context, { filename: assetPath });
  return context.RTCPeerConnection;
}

const stunUrl = "stun:stun.l.google.com:19302";
const originalConfiguration = {
  iceServers: [{ urls: stunUrl }],
  iceCandidatePoolSize: 4,
};

test("loads authorized ICE configuration before creating the initial offer", async () => {
  const turnServer = {
    urls: "turn:relay.example.invalid:3478?transport=udp",
    username: "short-lived-user",
    credential: "short-lived-password",
    credentialType: "password",
  };
  const PeerConnection = loadPeerConnection(async (url, options) => {
    assert.equal(url, "/api/voice/ice-config");
    assert.equal(options.credentials, "same-origin");
    assert.equal(options.cache, "no-store");
    return {
      ok: true,
      json: async () => ({
        turn_configured: true,
        ice_servers: [{ urls: stunUrl }, turnServer],
      }),
    };
  });

  const peer = new PeerConnection(originalConfiguration);
  const offer = await peer.createOffer({ offerToReceiveAudio: true });

  assert.equal(offer.type, "offer");
  assert.deepEqual(peer.calls, ["setConfiguration", "createOffer"]);
  assert.equal(peer.configuration.iceCandidatePoolSize, 4);
  assert.equal(peer.configuration.iceServers.length, 2);
  assert.equal(peer.configuration.iceServers[1].urls, turnServer.urls);
  assert.equal(
    peer.configuration.iceServers[1].credential,
    turnServer.credential,
  );
});

test("applies ICE configuration before accepting a remote offer", async () => {
  const PeerConnection = loadPeerConnection(async () => ({
    ok: true,
    json: async () => ({
      ice_servers: [{ urls: "turns:relay.example.invalid:5349?transport=tcp" }],
    }),
  }));
  const peer = new PeerConnection(originalConfiguration);

  await peer.setRemoteDescription({ type: "offer", sdp: "synthetic" });

  assert.deepEqual(peer.calls, ["setConfiguration", "setRemoteDescription"]);
  assert.equal(
    peer.configuration.iceServers[0].urls,
    "turns:relay.example.invalid:5349?transport=tcp",
  );
});

test("falls back to the bundled STUN server if the ICE endpoint is unavailable", async () => {
  const PeerConnection = loadPeerConnection(async () => {
    throw new Error("temporary network error");
  });
  const peer = new PeerConnection(originalConfiguration);

  const answer = await peer.createAnswer();

  assert.equal(answer.type, "answer");
  assert.deepEqual(peer.calls, ["createAnswer"]);
  assert.equal(peer.configuration.iceServers[0].urls, stunUrl);
});

test("rejects non-ICE URL schemes and preserves the original configuration", async () => {
  const PeerConnection = loadPeerConnection(async () => ({
    ok: true,
    json: async () => ({ ice_servers: [{ urls: "https://attacker.invalid/" }] }),
  }));
  const peer = new PeerConnection(originalConfiguration);

  await peer.createOffer();

  assert.deepEqual(peer.calls, ["createOffer"]);
  assert.equal(peer.configuration.iceServers[0].urls, stunUrl);
});

test("loads the ICE adapter before the portal module", () => {
  const html = readFileSync(indexPath, "utf8");
  const adapterIndex = html.indexOf("/assets/voice-ice-config-20261016.js");
  const portalModuleIndex = html.indexOf('type="module" crossorigin src="/assets/index-');

  assert.notEqual(adapterIndex, -1);
  assert.notEqual(portalModuleIndex, -1);
  assert.ok(adapterIndex < portalModuleIndex);
});
