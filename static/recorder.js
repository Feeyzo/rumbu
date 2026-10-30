// Records from the microphone and returns a small mono 16 kHz WAV file,
// a format Africa's Talking can <Play> and every browser can play back.
window.RumbuRecorder = class {
  async start() {
    this.stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true } });
    this.chunks = [];
    this.rec = new MediaRecorder(this.stream);
    this.rec.ondataavailable = e => e.data.size && this.chunks.push(e.data);
    this.rec.start();
    this.started = Date.now();
  }

  stop() {
    return new Promise((resolve, reject) => {
      this.rec.onstop = async () => {
        this.stream.getTracks().forEach(t => t.stop());
        try { resolve(await RumbuRecorder.toWav(new Blob(this.chunks, { type: this.rec.mimeType }))); }
        catch (e) { reject(e); }
      };
      this.rec.stop();
    });
  }

  static async toWav(blob, rate = 16000) {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const decoded = await ctx.decodeAudioData(await blob.arrayBuffer());
    ctx.close();
    const off = new OfflineAudioContext(1, Math.max(1, Math.ceil(decoded.duration * rate)), rate);
    const src = off.createBufferSource();
    src.buffer = decoded; src.connect(off.destination); src.start();
    const pcm = (await off.startRendering()).getChannelData(0);
    // trim leading/trailing silence so prompts start promptly
    let a = 0, b = pcm.length - 1;
    while (a < b && Math.abs(pcm[a]) < 0.01) a++;
    while (b > a && Math.abs(pcm[b]) < 0.01) b--;
    a = Math.max(0, a - rate * 0.1); b = Math.min(pcm.length - 1, b + rate * 0.2);
    const data = pcm.subarray(a, b + 1);
    const buf = new ArrayBuffer(44 + data.length * 2), v = new DataView(buf);
    const str = (o, s) => [...s].forEach((c, i) => v.setUint8(o + i, c.charCodeAt(0)));
    str(0, 'RIFF'); v.setUint32(4, 36 + data.length * 2, true); str(8, 'WAVE');
    str(12, 'fmt '); v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true);
    v.setUint32(24, rate, true); v.setUint32(28, rate * 2, true); v.setUint16(32, 2, true); v.setUint16(34, 16, true);
    str(36, 'data'); v.setUint32(40, data.length * 2, true);
    for (let i = 0; i < data.length; i++) v.setInt16(44 + i * 2, Math.max(-1, Math.min(1, data[i])) * 0x7fff, true);
    return new Blob([buf], { type: 'audio/wav' });
  }
};
