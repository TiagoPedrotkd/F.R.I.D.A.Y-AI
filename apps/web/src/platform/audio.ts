/** Mic capture — MediaRecorder today; desktop adapter later. */

function floatTo16BitPCM(float32: Float32Array): Int16Array {
  const out = new Int16Array(float32.length)
  for (let i = 0; i < float32.length; i++) {
    const s = Math.max(-1, Math.min(1, float32[i]!))
    out[i] = s < 0 ? s * 0x8000 : s * 0x7fff
  }
  return out
}

function encodeWav(samples: Float32Array, sampleRate: number): Blob {
  const pcm = floatTo16BitPCM(samples)
  const buffer = new ArrayBuffer(44 + pcm.byteLength)
  const view = new DataView(buffer)
  const writeStr = (offset: number, str: string) => {
    for (let i = 0; i < str.length; i++) view.setUint8(offset + i, str.charCodeAt(i))
  }
  writeStr(0, 'RIFF')
  view.setUint32(4, 36 + pcm.byteLength, true)
  writeStr(8, 'WAVE')
  writeStr(12, 'fmt ')
  view.setUint32(16, 16, true)
  view.setUint16(20, 1, true)
  view.setUint16(22, 1, true)
  view.setUint32(24, sampleRate, true)
  view.setUint32(28, sampleRate * 2, true)
  view.setUint16(32, 2, true)
  view.setUint16(34, 16, true)
  writeStr(36, 'data')
  view.setUint32(40, pcm.byteLength, true)
  new Int16Array(buffer, 44).set(pcm)
  return new Blob([buffer], { type: 'audio/wav' })
}

export type MicRecorder = {
  stop: () => Promise<Blob>
  cancel: () => void
}

export async function startMicRecording(): Promise<MicRecorder> {
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: {
      echoCancellation: true,
      noiseSuppression: true,
      channelCount: 1,
    },
  })
  const ctx = new AudioContext({ sampleRate: 16000 })
  const source = ctx.createMediaStreamSource(stream)
  const processor = ctx.createScriptProcessor(4096, 1, 1)
  const chunks: Float32Array[] = []
  processor.onaudioprocess = (e) => {
    const input = e.inputBuffer.getChannelData(0)
    chunks.push(new Float32Array(input))
  }
  source.connect(processor)
  processor.connect(ctx.destination)

  let settled = false
  const cleanup = () => {
    processor.disconnect()
    source.disconnect()
    stream.getTracks().forEach((t) => t.stop())
    void ctx.close()
  }

  return {
    stop: async () => {
      if (settled) return new Blob()
      settled = true
      cleanup()
      const total = chunks.reduce((n, c) => n + c.length, 0)
      const merged = new Float32Array(total)
      let offset = 0
      for (const c of chunks) {
        merged.set(c, offset)
        offset += c.length
      }
      return encodeWav(merged, ctx.sampleRate || 16000)
    },
    cancel: () => {
      if (settled) return
      settled = true
      cleanup()
    },
  }
}

export async function playWavBytes(
  bytes: ArrayBuffer,
  opts: { volume?: number; signal?: AbortSignal } = {},
): Promise<void> {
  const audio = new Audio()
  const blob = new Blob([bytes], { type: 'audio/wav' })
  const url = URL.createObjectURL(blob)
  audio.src = url
  audio.volume = opts.volume ?? 1
  const cleanup = () => URL.revokeObjectURL(url)
  return new Promise((resolve, reject) => {
    const onAbort = () => {
      audio.pause()
      cleanup()
      resolve()
    }
    opts.signal?.addEventListener('abort', onAbort)
    audio.onended = () => {
      cleanup()
      resolve()
    }
    audio.onerror = () => {
      cleanup()
      reject(new Error('Playback failed'))
    }
    void audio.play().catch(reject)
  })
}
