import type { Preview } from '@storybook/react'
import { applyTheme, type ThemeMode } from '../src/styles/system'
import '../src/index.css'

const preview: Preview = {
  globalTypes: {
    theme: {
      description: 'HUD color theme',
      defaultValue: 'dark',
      toolbar: {
        title: 'Theme',
        icon: 'circlehollow',
        items: [
          { value: 'dark', title: 'Dark' },
          { value: 'light', title: 'Light' },
        ],
        dynamicTitle: true,
      },
    },
    highContrast: {
      description: 'High contrast',
      defaultValue: false,
      toolbar: {
        title: 'Contrast',
        icon: 'contrast',
        items: [
          { value: false, title: 'Normal' },
          { value: true, title: 'High contrast' },
        ],
        dynamicTitle: true,
      },
    },
  },
  decorators: [
    (Story, context) => {
      const mode = (context.globals.theme as ThemeMode) || 'dark'
      const highContrast = Boolean(context.globals.highContrast)
      applyTheme({ mode, highContrast, reducedMotion: false })
      return (
        <div className="hud-viewport min-h-[240px] p-6">
          <div className="hud-stage relative">
            <Story />
          </div>
        </div>
      )
    },
  ],
  parameters: {
    layout: 'fullscreen',
    controls: { matchers: { color: /(background|color)$/i, date: /Date$/i } },
  },
}

export default preview
