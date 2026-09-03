export type Prefs = {
  language: 'pt' | 'en'
  theme: 'dark' | 'light'
  userAddress: string
  ttsEnabled: boolean
  volume: number
  rate: number
  autoplay: boolean
  interrupt: boolean
  autoOpenMonitors: boolean
  highContrast: boolean
  reducedMotion: boolean
  demoMode: boolean
  workingHours: string
  preferredMeetingDuration: number
  doNotDisturb: string
}

export const defaultPrefs: Prefs = {
  language: 'pt',
  theme: 'dark',
  userAddress: 'Senhor',
  ttsEnabled: true,
  volume: 0.9,
  rate: 1,
  autoplay: true,
  interrupt: true,
  autoOpenMonitors: false,
  highContrast: false,
  reducedMotion: false,
  demoMode: false,
  workingHours: '9:00-18:00',
  preferredMeetingDuration: 30,
  doNotDisturb: '22:00-8:00',
}

export const DEMO_FIXTURES = {
  banner: 'Modo demonstração — respostas etiquetadas, não são dados em tempo real.',
  chat: {
    reply:
      '[DEMO] Olá — sou a F.R.I.D.A.Y. O LM Studio não está disponível, por isso esta resposta é uma simulação.',
    activity: [
      { label: 'A interpretar o pedido…', status: 'done' },
      { label: '[DEMO] Sem ligação ao modelo', status: 'done' },
      { label: 'Concluído.', status: 'done' },
    ],
    ui: {
      sources: [
        {
          title: '[DEMO] Exemplo de fonte',
          url: 'https://example.com',
          snippet: 'Isto não é uma pesquisa real.',
          source: 'demo',
        },
      ],
      country: 'PT',
      offer_monitor: true,
      monitor_path: '/monitors/world_snapshot.html',
      monitor_kind: 'world',
    },
    session: { last_country: 'PT', last_language: 'pt' },
  },
  news: {
    reply:
      '[DEMO] Notícias de exemplo para Portugal:\n- Titular fictício um\n- Titular fictício dois\nNão são dados reais.',
    activity: [
      { label: 'A interpretar o pedido…', status: 'done' },
      { label: '[DEMO] A consultar as noticias', status: 'done' },
      { label: 'Concluído.', status: 'done' },
    ],
    ui: {
      country: 'PT',
      kind: 'news',
      offer_monitor: true,
      monitor_path: '/monitors/world_snapshot.html',
      monitor_kind: 'world',
      headlines_only: true,
      sources: [
        {
          title: '[DEMO] Economia local estabiliza',
          url: 'https://example.com/1',
          source: 'Demo Wire',
        },
        {
          title: '[DEMO] Tecnologia e inovação',
          url: 'https://example.com/2',
          source: 'Demo Tech',
        },
      ],
    },
    session: { last_country: 'PT', last_news_context: 'news', last_language: 'pt' },
  },
}
