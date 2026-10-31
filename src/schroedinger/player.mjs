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

export function axisTicks(lo, hi) {
  const rough = (hi-lo)/4, power = 10**Math.floor(Math.log10(rough));
  const step = [1, 2, 5, 10].find(value => value*power >= rough)*power;
  const ticks = [];
  for (let value = Math.ceil(lo/step)*step; value <= hi+step*1e-8; value += step)
    ticks.push(Number(value.toPrecision(12)));
  return ticks;
}
export function colorValue(fraction, vmax, gamma) { return vmax*fraction**(1/gamma); }
const pretty = value => String(Number(Number(value).toPrecision(5)));

function drawAxes(ctx, box, xmin, xmax, ymin, ymax, xlabel, ylabel) {
  const {l, t, w, h} = box;
  ctx.strokeStyle = '#657384'; ctx.lineWidth = 1; ctx.strokeRect(l, t, w, h);
  ctx.fillStyle = '#263544'; ctx.font = '13px sans-serif';
  for (const value of axisTicks(xmin, xmax)) {
    ctx.textAlign = 'center'; ctx.fillText(pretty(value), l+(value-xmin)*w/(xmax-xmin), t+h+22);
  }
  for (const value of axisTicks(ymin, ymax)) {
    ctx.textAlign = 'right'; ctx.fillText(pretty(value), l-9, t+h-(value-ymin)*h/(ymax-ymin)+4);
  }
  ctx.textAlign = 'center'; ctx.fillText(xlabel, l+w/2, t+h+45);
  ctx.save(); ctx.translate(17, t+h/2); ctx.rotate(-Math.PI/2); ctx.fillText(ylabel, 0, 0); ctx.restore();
}
function drawLine(ctx, box, values, lo, hi, color) {
  ctx.save(); ctx.beginPath(); ctx.rect(box.l, box.t, box.w, box.h); ctx.clip();
  ctx.strokeStyle = color; ctx.lineWidth = 1.8; ctx.beginPath();
  values.forEach((value, i) => {
    const x = box.l+i*box.w/(values.length-1), y = box.t+box.h-(value-lo)*box.h/(hi-lo);
    if (i === 0) ctx.moveTo(x,y); else ctx.lineTo(x,y);
  });
  ctx.stroke(); ctx.restore();
}
function makePanel(panel, data) {
  panel.querySelector('h3').textContent = data.name;
  const canvas = panel.querySelector('.density'), ctx = canvas.getContext('2d');
  const available = Math.max(320, panel.clientWidth || 800);
  const box = {l:65, t:40, w:available-185, h:260};
  if (data.dimension === 2) {
    const scale = Math.min(box.w/(data.x_max-data.x_min), 450/(data.y_max-data.y_min));
    box.w = (data.x_max-data.x_min)*scale; box.h = (data.y_max-data.y_min)*scale;
  }
  canvas.width = Math.ceil(available); canvas.height = Math.ceil(box.t+box.h+60);
  const profile = panel.querySelector('.profile'), pctx = profile.getContext('2d');
  profile.width = canvas.width; profile.height = 225;
  const profileBox = {l:65,t:35,w:box.w,h:130};
  let images = [], densities;
  panel.querySelector('.solver').textContent = `Metode: ${data.solver} · Maks regnskapsavvik: ${Number(data.budget_error).toExponential(2)}`;
  if (data.dimension === 2) {
    panel.querySelector('.scale').textContent = `Tetthet |ψ|² · ${data.gamma === 1 ? 'lineær skala' : 'gamma 0,5 – svake mønstre fremhevet'} · felles, fast skala. ${pretty(100*data.clipped_fraction)} % av pikslene er over fargegrensen.`;
    panel.querySelector('.profile-note').textContent = `Øyeblikksprofil ved faktisk x = ${pretty(data.measurements.screen_x)}. Tetthet langs y; ikke akkumulert detektorsignal.`;
  } else profile.hidden = true;
  async function load() {
    if (data.dimension === 2) {
      images = await Promise.all(data.images.map(source => new Promise((resolve,reject) => {
        const image = new Image(); image.onload = () => resolve(image); image.onerror = reject; image.src = source;
      })));
    } else {
      const bytes = Uint8Array.from(atob(data.density), char => char.charCodeAt(0));
      const view = new DataView(bytes.buffer); densities = new Float32Array(bytes.length/4);
      for (let i=0; i<densities.length; i++) densities[i] = view.getFloat32(i*4,true);
    }
  }
  function draw(masterFrame, requested, comparing) {
    const frame = data.indices[masterFrame], physical = data.times[frame];
    ctx.fillStyle = 'white'; ctx.fillRect(0,0,canvas.width,canvas.height);
    if (data.dimension === 2) {
      ctx.imageSmoothingEnabled = true; ctx.drawImage(images[frame],box.l,box.t,box.w,box.h);
      for (let i=0;i<256;i++) {
        ctx.fillStyle = `rgb(${data.palette[255-i].join(',')})`;
        ctx.fillRect(box.l+box.w+20,box.t+i*box.h/256,17,box.h/256+1);
      }
      ctx.fillStyle='#263544'; ctx.font='12px sans-serif'; ctx.textAlign='left';
      for (let i=0;i<=4;i++) ctx.fillText(`${i===0?'≥ ':''}${pretty(colorValue(1-i/4,data.vmax,data.gamma))}`,box.l+box.w+43,box.t+i*box.h/4+4);
      drawAxes(ctx,box,data.x_min,data.x_max,data.y_min,data.y_max,'x','y');
      pctx.fillStyle='white'; pctx.fillRect(0,0,profile.width,profile.height);
      drawLine(pctx,profileBox,data.measurements.profile[frame],0,data.profile_max,'#126b8c');
      const ys=data.measurements.y;
      drawAxes(pctx,profileBox,ys[0],ys[ys.length-1],0,data.profile_max,'y','Tetthet |ψ|²');
      pctx.fillStyle='#263544';pctx.textAlign='center';pctx.font='14px sans-serif';
      pctx.fillText(`Profil ved x = ${pretty(data.measurements.screen_x)}, t = ${pretty(physical)}`,box.l+box.w/2,20);
    } else {
      drawLine(ctx,box,densities.subarray(frame*data.nx,(frame+1)*data.nx),0,data.density_max,'#126b8c');
      drawAxes(ctx,box,data.x_min,data.x_max,0,data.density_max,'x','Tetthet |ψ|²');
      if (data.potential.length) {
        const lo=Math.min(0,...data.potential), hi=Math.max(...data.potential);
        drawLine(ctx,box,data.potential,lo,hi,'#b66b12');
        ctx.fillStyle='#92520a';ctx.font='13px sans-serif';ctx.textAlign='left';
        for (const value of axisTicks(lo,hi)) ctx.fillText(pretty(value),box.l+box.w+9,box.t+box.h-(value-lo)*box.h/(hi-lo)+4);
        ctx.save();ctx.translate(box.l+box.w+78,box.t+box.h/2);ctx.rotate(-Math.PI/2);
        ctx.textAlign='center';ctx.fillText('Potensial V (egen akse)',0,0);ctx.restore();
      }
    }
    ctx.fillStyle='#263544';ctx.font='16px sans-serif';ctx.textAlign='center';
    ctx.fillText(`t = ${pretty(physical)}    P = ${Number(data.probability[frame]).toFixed(6)}`,box.l+box.w/2,24);
    canvas.setAttribute('aria-label',`${data.name}: sannsynlighetstetthet ved t = ${pretty(physical)}`);
    panel.dataset.frame=String(frame);panel.dataset.time=String(physical);
    for (const [role,value] of [['time',pretty(physical)],['probability',Number(data.probability[frame]).toFixed(6)],['absorbed',Number(data.absorbed[frame]).toFixed(6)]])
      panel.querySelector(`[data-role="${role}"]`).textContent=value;
    panel.querySelector('.time-offset').textContent = comparing ? `Avvik fra felles ønsket tid: ${pretty(physical-requested)}. Nærmeste lagrede bilde vises.` : '';
    const regions=data.measurements.regions, regionText=panel.querySelector('.regions');
    regionText.hidden=!regions;
    if (regions) regionText.textContent=`P til venstre: ${regions.left[frame].toFixed(5)} · I barriereområdet: ${regions.barrier[frame].toFixed(5)} · Til høyre: ${regions.right[frame].toFixed(5)}`;
  }
  return {load,draw,canvas,profile,panel};
}

export default function ({data,parentElement}) {
  const root=parentElement.querySelector('.player');
  root.querySelector('.panels').replaceChildren();
  const hosts=data.runs.map(()=>{
    const panel=root.querySelector('template').content.firstElementChild.cloneNode(true);
    root.querySelector('.panels').append(panel);return panel;
  });
  const panels=data.runs.map((item,i)=>makePanel(hosts[i],item));
  const play=root.querySelector('[data-action="play"]'), restart=root.querySelector('[data-action="restart"]');
  const download=root.querySelector('[data-action="download"]'), speed=root.querySelector('select');
  const slider=root.querySelector('input[type="range"]'), status=root.querySelector('.status');
  const prior=parentElement.olympiaPlayback;
  const clock=new PlaybackClock(data.times.length,prior?.id===data.id?prior.clock.fps:12);
  if(prior?.id===data.id) clock.seek(prior.clock.frame);
  parentElement.olympiaPlayback={id:data.id,clock};
  let disposed=false, ready=false, animation=0, shown=-1;
  slider.max=String(clock.count-1);slider.value=String(clock.frame);speed.value=String(clock.fps);
  function updateButton(){play.textContent=clock.playing?'Pause':'Spill av';play.setAttribute('aria-pressed',String(clock.playing));}
  function draw(frame){
    if(!ready||disposed)return;
    panels.forEach(panel=>panel.draw(frame,data.times[frame],panels.length>1));
    slider.value=String(frame);slider.setAttribute('aria-valuetext',`Bilde ${frame+1} av ${clock.count}, ønsket t = ${pretty(data.times[frame])}`);
    root.dataset.frame=String(frame);root.querySelector('[data-role="frame-label"]').textContent=`${frame+1} / ${clock.count}`;
    root.querySelector('.requested-time').textContent=`${panels.length>1?'Felles ønsket fysisk tid':'Fysisk tid'}: ${pretty(data.times[frame])}`;
    shown=frame;
  }
  function tick(now){
    if(disposed||!clock.playing)return;
    const frame=clock.tick(now);if(frame!==shown)draw(frame);updateButton();
    if(clock.playing)animation=requestAnimationFrame(tick);
  }
  function schedule(){cancelAnimationFrame(animation);updateButton();animation=requestAnimationFrame(tick);}
  play.onclick=()=>{if(clock.playing){clock.pause();cancelAnimationFrame(animation);updateButton();}
    else{clock.play(performance.now());draw(clock.frame);schedule();}};
  restart.onclick=()=>{clock.restart(performance.now());draw(0);schedule();};
  slider.oninput=()=>{clock.seek(Number(slider.value));cancelAnimationFrame(animation);draw(clock.frame);updateButton();};
  speed.onchange=()=>clock.setRate(Number(speed.value),performance.now());
  download.onclick=()=>{
    const image=document.createElement('canvas');image.width=panels.reduce((sum,p)=>sum+p.canvas.width,0);
    image.height=Math.max(...panels.map(p=>p.canvas.height+(data.runs[0].dimension===2?p.profile.height:0)))+35;
    const ctx=image.getContext('2d');ctx.fillStyle='white';ctx.fillRect(0,0,image.width,image.height);
    let x=0;panels.forEach((panel,i)=>{ctx.fillStyle='#263544';ctx.font='18px sans-serif';ctx.fillText(data.runs[i].name,x+75,24);
      ctx.drawImage(panel.canvas,x,35);if(data.runs[i].dimension===2)ctx.drawImage(panel.profile,x,35+panel.canvas.height);x+=panel.canvas.width;});
    image.toBlob(blob=>{if(!blob)return;const url=URL.createObjectURL(blob),anchor=document.createElement('a');
      anchor.href=url;anchor.download='snapshot.png';anchor.click();setTimeout(()=>URL.revokeObjectURL(url),1000);},'image/png');
  };
  const hide=()=>{if(document.hidden){clock.pause();cancelAnimationFrame(animation);updateButton();}};
  document.addEventListener('visibilitychange',hide);
  Promise.all(panels.map(panel=>panel.load())).then(()=>{
    if(disposed)return;ready=true;
    for(const element of [play,restart,download,speed,slider])element.disabled=false;
    status.textContent=`${clock.count} ${panels.length>1?'felles tidspunkter · synkronisert sammenlikning':'lagrede bilder'} · avspilling i nettleseren`;
    draw(clock.frame);updateButton();
  }).catch(()=>{if(!disposed)status.textContent='Kunne ikke klargjøre bildene. Velg kjøringen på nytt.';});
  return()=>{disposed=true;clock.pause();cancelAnimationFrame(animation);document.removeEventListener('visibilitychange',hide);};
}
