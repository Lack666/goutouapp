export const tokens = {
  space: { xs: 4, sm: 8, md: 12, lg: 16, xl: 24, xxl: 32, hero: 48 },
  radius: { sm: 12, md: 20, pill: 999 },
  type: {
    title: { fontSize: 28, lineHeight: 38, fontWeight: '700' },
    heading: { fontSize: 20, lineHeight: 29, fontWeight: '600' },
    body: { fontSize: 16, lineHeight: 25, fontWeight: '400' },
    caption: { fontSize: 13, lineHeight: 21, fontWeight: '400' },
    button: { fontSize: 16, lineHeight: 24, fontWeight: '600' },
  },
  layout: { maxWidth: 680, touchTarget: 48 },
} as const;

export const palettes = {
  light: {
    background: '#F5F4EE',
    surface: '#FFFFFF',
    text: '#202E2B',
    muted: '#586B65',
    primary: '#245A48',
    onPrimary: '#FFFFFF',
    border: '#D7DFD9',
    tint: '#E8F1E9',
    danger: '#A63235',
    disabled: '#E0E5E0',
  },
  dark: {
    background: '#101C18',
    surface: '#1B2B24',
    text: '#EFF4ED',
    muted: '#B2C4B9',
    primary: '#A3DDBA',
    onPrimary: '#132A1E',
    border: '#3C5145',
    tint: '#293E31',
    danger: '#FFB4B5',
    disabled: '#34493C',
  },
} as const;

export type ThemeColors = { [Key in keyof typeof palettes.light]: string };
