// All animation is local. No Streamlit state/trigger messages are sent per frame.
export function advanceFrame(frame, updated, now, fps, count) {
  if (!(fps > 0) || !Number.isFinite(fps) || count < 1 || frame < 0 || frame >= count)
    throw new Error("Invalid playback clock");
  const steps = Math.floor(Math.max(0, now - updated) * fps / 1000 + 1e-9);
  const index = Math.min(frame + steps, count - 1);
  return { index, updated: updated + steps * 1000 / fps, playing: index < count - 1 };
}

export class PlaybackClock {
  constructor(count, fps = 12) {
    if (!Number.isInteger(count) || count < 1) throw new Error("Empty playback");
    this.count = count; this.frame = count - 1; this.playing = false;
    this.setRate(fps, 0);
  }
  play(now) { if (this.frame === this.count - 1) this.frame = 0; this.playing = true; this.updated = now; }
  pause() { this.playing = false; }
  restart(now) { this.frame = 0; this.playing = true; this.updated = now; }
  seek(frame) { this.frame = Math.max(0, Math.min(this.count - 1, Math.round(frame))); this.pause(); }
  setRate(fps, now) {
    if (!(fps > 0) || !Number.isFinite(fps)) throw new Error("Invalid rate");
    this.fps = fps; this.updated = now;
  }
  tick(now) {
    if (this.playing) {
      const next = advanceFrame(this.frame, this.updated, now, this.fps, this.count);
      this.frame = next.index; this.updated = next.updated; this.playing = next.playing;
    }
    return this.frame;
  }
}

export default function ({ data, parentElement }) {
  const root = parentElement.querySelector(".player");
  const canvas = root.querySelector("canvas"), ctx = canvas.getContext("2d");
  const play = root.querySelector('[data-action="play"]');
  const restart = root.querySelector('[data-action="restart"]');
  const download = root.querySelector('[data-action="download"]');
  const speed = root.querySelector("select"), slider = root.querySelector('input[type="range"]');
  const status = root.querySelector(".status");
  const prior = parentElement.olympiaPlayback;
  const clock = new PlaybackClock(data.times.length, prior?.id === data.id ? prior.clock.fps : 12);
  if (prior?.id === data.id) clock.seek(prior.clock.frame);
  parentElement.olympiaPlayback = { id: data.id, clock };
  let disposed = false, ready = false, animation = 0, shown = -1;
  let images = [], densities = null;
  const L = 74, R = data.dimension === 2 ? 110 : 74, T = 45, B = 58;
  const xSpan = data.x_max - data.x_min;
  let pw = 800, ph = 360;
  if (data.dimension === 2) {
    const scale = Math.min(800 / xSpan, 480 / (data.y_max - data.y_min));
    pw = xSpan * scale; ph = (data.y_max - data.y_min) * scale;
  }
  canvas.width = Math.ceil(L + pw + R); canvas.height = Math.ceil(T + ph + B);
  slider.max = String(clock.count - 1); slider.value = String(clock.frame);
  speed.value = String(clock.fps);
  const pretty = value => String(Number(Number(value).toPrecision(6)));
  const text = (role, value) => { root.querySelector(`[data-role="${role}"]`).textContent = value; };
  text("solver", `Metode: ${data.solver}`);
  text("budget", `Maks regnskapsavvik: ${Number(data.budget_error).toExponential(2)}`);

  function line(values, lo, hi, color) {
    ctx.strokeStyle = color; ctx.lineWidth = 1.8; ctx.beginPath();
    for (let i = 0; i < values.length; i++) {
      const x = L + i * pw / (values.length - 1), y = T + ph - (values[i] - lo) * ph / (hi - lo);
      if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    }
    ctx.stroke();
  }
  function draw(frame) {
    if (!ready || disposed) return;
    ctx.fillStyle = "white"; ctx.fillRect(0, 0, canvas.width, canvas.height);
    if (data.dimension === 2) {
      ctx.imageSmoothingEnabled = true;
      ctx.drawImage(images[frame], L, T, pw, ph);
      for (let i = 0; i < 256; i++) {
        ctx.fillStyle = `rgb(${data.palette[255 - i].join(",")})`;
        ctx.fillRect(L + pw + 24, T + i * ph / 256, 17, ph / 256 + 1);
      }
      ctx.fillStyle = "#20252c"; ctx.font = "12px sans-serif"; ctx.textAlign = "left";
      for (let i = 0; i <= 4; i++) ctx.fillText(pretty(data.vmax * (1 - i / 4)), L + pw + 46, T + i * ph / 4 + 4);
    } else {
      const values = densities.subarray(frame * data.nx, (frame + 1) * data.nx);
      line(values, 0, data.density_max, "#246888");
      if (data.potential.length) {
        const lo = Math.min(...data.potential), hi = Math.max(...data.potential);
        line(data.potential, lo, hi, "#c8882e");
        ctx.font = "12px sans-serif"; ctx.fillStyle = "#99661d"; ctx.textAlign = "left";
        ctx.fillText(`V: ${pretty(lo)} … ${pretty(hi)}`, L + pw - 170, T + 17);
      }
    }
    ctx.strokeStyle = "#343942"; ctx.lineWidth = 1; ctx.strokeRect(L, T, pw, ph);
    ctx.font = "13px sans-serif"; ctx.fillStyle = "#20252c";
    for (let i = 0; i <= 4; i++) {
      const x = L + i * pw / 4;
      ctx.textAlign = "center"; ctx.fillText(pretty(data.x_min + i * xSpan / 4), x, T + ph + 22);
      const y = T + ph - i * ph / 4;
      const value = data.dimension === 2 ? data.y_min + i * (data.y_max - data.y_min) / 4 : i * data.density_max / 4;
      ctx.textAlign = "right"; ctx.fillText(pretty(value), L - 12, y + 4);
    }
    ctx.textAlign = "center"; ctx.fillText("x", L + pw / 2, T + ph + 46);
    ctx.save(); ctx.translate(19, T + ph / 2); ctx.rotate(-Math.PI / 2);
    ctx.fillText(data.dimension === 2 ? "y" : "Probability density", 0, 0); ctx.restore();
    ctx.font = "16px sans-serif";
    ctx.fillText(`t = ${pretty(data.times[frame])}    P = ${Number(data.probability[frame]).toFixed(6)}`, L + pw / 2, 24);
    slider.value = String(frame);
    slider.setAttribute("aria-valuetext", `Bilde ${frame + 1} av ${clock.count}, t = ${pretty(data.times[frame])}`);
    canvas.setAttribute("aria-label", `Sannsynlighetstetthet ved t = ${pretty(data.times[frame])}`);
    root.dataset.frame = String(frame);
    text("frame-label", `${frame + 1} / ${clock.count}`);
    text("time", pretty(data.times[frame]));
    text("probability", Number(data.probability[frame]).toFixed(6));
    text("absorbed", Number(data.absorbed[frame]).toFixed(6));
    shown = frame;
  }
  function updateButton() {
    play.textContent = clock.playing ? "Pause" : "Spill av";
    play.setAttribute("aria-pressed", String(clock.playing));
  }
  function tick(now) {
    if (disposed || !clock.playing) return;
    const frame = clock.tick(now);
    if (frame !== shown) draw(frame);
    updateButton();
    if (clock.playing) animation = requestAnimationFrame(tick);
  }
  function schedule() { cancelAnimationFrame(animation); updateButton(); animation = requestAnimationFrame(tick); }
  play.onclick = () => {
    if (clock.playing) { clock.pause(); cancelAnimationFrame(animation); updateButton(); }
    else { clock.play(performance.now()); draw(clock.frame); schedule(); }
  };
  restart.onclick = () => { clock.restart(performance.now()); draw(0); schedule(); };
  slider.oninput = () => { clock.seek(Number(slider.value)); cancelAnimationFrame(animation); draw(clock.frame); updateButton(); };
  speed.onchange = () => { clock.setRate(Number(speed.value), performance.now()); };
  download.onclick = () => canvas.toBlob(blob => {
    if (!blob) return;
    const url = URL.createObjectURL(blob), anchor = document.createElement("a");
    anchor.href = url; anchor.download = "snapshot.png"; anchor.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }, "image/png");
  const hide = () => { if (document.hidden) { clock.pause(); cancelAnimationFrame(animation); updateButton(); } };
  document.addEventListener("visibilitychange", hide);
  async function load() {
    try {
      if (data.dimension === 2) {
        let loaded = 0;
        images = await Promise.all(data.images.map(source => new Promise((resolve, reject) => {
          const image = new Image();
          image.onload = () => {
            loaded++;
            if (!disposed) status.textContent = `Klargjør bilder: ${loaded} / ${data.images.length}`;
            resolve(image);
          };
          image.onerror = reject; image.src = source;
        })));
      } else {
        const bytes = Uint8Array.from(atob(data.density), character => character.charCodeAt(0));
        const view = new DataView(bytes.buffer); densities = new Float32Array(bytes.length / 4);
        for (let i = 0; i < densities.length; i++) densities[i] = view.getFloat32(i * 4, true);
      }
      if (disposed) return;
      ready = true;
      for (const element of [play, restart, download, speed, slider]) element.disabled = false;
      status.textContent = `${clock.count} lagrede bilder · avspilling i nettleseren`;
      draw(clock.frame); updateButton();
    } catch (_) {
      if (!disposed) status.textContent = "Kunne ikke klargjøre bildene. Oppdater siden og prøv igjen.";
    }
  }
  load();
  return () => {
    disposed = true; clock.pause(); cancelAnimationFrame(animation);
    document.removeEventListener("visibilitychange", hide);
  };
}
