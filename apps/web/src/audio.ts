// Record PCM WAV for server-verifiable duration. No third-party transcription or audio service.
export async function recordWav(onStatus:(s:string)=>void):Promise<File>{
  const stream=await navigator.mediaDevices.getUserMedia({audio:true});
  const context=new AudioContext({sampleRate:16000});
  const source=context.createMediaStreamSource(stream),processor=context.createScriptProcessor(4096,1,1);
  const chunks:Float32Array[]=[];processor.onaudioprocess=e=>chunks.push(new Float32Array(e.inputBuffer.getChannelData(0)));
  source.connect(processor);processor.connect(context.destination);onStatus('Recording 10 seconds of fictional stock information…');
  await new Promise(resolve=>setTimeout(resolve,10000));processor.disconnect();source.disconnect();stream.getTracks().forEach(t=>t.stop());
  const rate=context.sampleRate;await context.close();const count=chunks.reduce((n,c)=>n+c.length,0);
  const buffer=new ArrayBuffer(44+count*2),view=new DataView(buffer);const str=(at:number,s:string)=>[...s].forEach((c,i)=>view.setUint8(at+i,c.charCodeAt(0)));
  str(0,'RIFF');view.setUint32(4,36+count*2,true);str(8,'WAVE');str(12,'fmt ');view.setUint32(16,16,true);view.setUint16(20,1,true);view.setUint16(22,1,true);view.setUint32(24,rate,true);view.setUint32(28,rate*2,true);view.setUint16(32,2,true);view.setUint16(34,16,true);str(36,'data');view.setUint32(40,count*2,true);
  let i=44;for(const chunk of chunks)for(const value of chunk){view.setInt16(i,Math.max(-1,Math.min(1,value))*32767,true);i+=2;}
  return new File([buffer],'synthetic-recording.wav',{type:'audio/wav'});
}
