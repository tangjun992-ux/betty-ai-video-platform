const { fontFamily } = require("tailwindcss/defaultTheme")

/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ["class"],
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
  	container: {
  		center: true,
  		padding: '2rem',
  		screens: {
  			'2xl': '1400px'
  		}
  	},
  	extend: {
  		colors: {
  			'cosmic-void': 'hsl(var(--cosmic-void) / <alpha-value>)',
  			'cosmic-deep': 'hsl(var(--cosmic-deep) / <alpha-value>)',
  			'cosmic-surface': 'hsl(var(--cosmic-surface) / <alpha-value>)',
  			'cosmic-elevated': 'hsl(var(--cosmic-elevated) / <alpha-value>)',
  			'cosmic-subtle': 'hsl(var(--cosmic-subtle) / <alpha-value>)',
			'cosmic-border': 'hsl(var(--cosmic-border) / <alpha-value>)',
			'cosmic-border-hover': 'hsl(var(--cosmic-border-hover) / <alpha-value>)',
			// Surface tiers (Lovable-style, 3-level elevation)
			'surface-1': 'hsl(var(--cosmic-surface) / <alpha-value>)',
			'surface-2': 'hsl(var(--cosmic-elevated) / <alpha-value>)',
			'surface-3': 'hsl(var(--cosmic-subtle) / <alpha-value>)',
			// Hairline borders (Lovable-inspired ultra-thin dividers)
			hairline: 'hsl(var(--cosmic-border) / 0.5)',
			'hairline-strong': 'hsl(var(--cosmic-border-hover) / <alpha-value>)',
  			'accent-cyan': 'hsl(var(--accent-cyan) / <alpha-value>)',
  			'accent-blue': 'hsl(var(--accent-blue) / <alpha-value>)',
  			'accent-violet': 'hsl(var(--accent-violet) / <alpha-value>)',
  			'accent-purple': 'hsl(var(--accent-purple) / <alpha-value>)',
  			'accent-fuchsia': 'hsl(var(--accent-fuchsia) / <alpha-value>)',
  			'text-primary': 'hsl(var(--text-primary) / <alpha-value>)',
  			'text-secondary': 'hsl(var(--text-secondary) / <alpha-value>)',
  			'text-tertiary': 'hsl(var(--text-tertiary) / <alpha-value>)',
  			'text-disabled': 'hsl(var(--text-disabled) / <alpha-value>)',
  			success: {
  				DEFAULT: 'hsl(var(--success) / <alpha-value>)',
  				foreground: 'hsl(0 0% 100%)',
  				muted: 'hsl(var(--success) / 0.10)'
  			},
  			warning: {
  				DEFAULT: 'hsl(var(--warning) / <alpha-value>)',
  				foreground: 'hsl(0 0% 100%)',
  				muted: 'hsl(var(--warning) / 0.12)'
  			},
  			destructive: {
  				DEFAULT: 'hsl(var(--destructive) / <alpha-value>)',
  				foreground: 'hsl(0 0% 100%)',
  				muted: 'hsl(var(--destructive) / 0.10)'
  			},
  			info: {
  				DEFAULT: 'hsl(var(--info) / <alpha-value>)',
  				foreground: 'hsl(0 0% 100%)',
  				muted: 'hsl(var(--info) / 0.10)'
  			},
			brand: {
				'50': '#f0faf8',
				'100': '#d5f0eb',
				'200': '#abe1d7',
				'300': '#6fc9bb',
				'400': '#3aada0',
				'500': '#0f766e',
				'600': '#0d9488',
				'700': '#0f766e',
				'800': '#115e59',
				'900': '#134e4a',
				DEFAULT: 'hsl(var(--brand) / <alpha-value>)',
				strong: 'hsl(var(--brand-strong) / <alpha-value>)',
				soft: 'hsl(var(--brand-soft) / <alpha-value>)'
			}
  		},
  		borderRadius: {
  			xs: '0.25rem',
  			sm: '0.375rem',
  			md: '0.5rem',
  			lg: '0.75rem',
  			xl: '1rem',
  			'2xl': '1.25rem',
  			'3xl': '1.5rem'
  		},
		fontFamily: {
			sans: [
				'var(--font-sans)',
                    ...fontFamily.sans
                ],
			display: [
				'var(--font-display)',
                    ...fontFamily.serif
                ],
			mono: [
				'var(--font-mono)',
                    ...fontFamily.mono
                ]
		},
  		fontSize: {
  			hero: [
  				'4.25rem',
  				{
  					lineHeight: '1.04',
  					letterSpacing: '-0.035em',
  					fontWeight: '600'
  				}
  			],
  			h1: [
  				'2.75rem',
  				{
  					lineHeight: '1.08',
  					letterSpacing: '-0.028em',
  					fontWeight: '600'
  				}
  			],
  			h2: [
  				'1.875rem',
  				{
  					lineHeight: '1.18',
  					letterSpacing: '-0.022em',
  					fontWeight: '650'
  				}
  			],
  			h3: [
  				'1.3125rem',
  				{
  					lineHeight: '1.3',
  					letterSpacing: '-0.016em',
  					fontWeight: '600'
  				}
  			],
  			h4: [
  				'1.125rem',
  				{
  					lineHeight: '1.4',
  					letterSpacing: '-0.011em',
  					fontWeight: '600'
  				}
  			],
  			body: [
  				'1rem',
  				{
  					lineHeight: '1.65',
  					letterSpacing: '-0.011em'
  				}
  			],
  			'body-sm': [
  				'0.875rem',
  				{
  					lineHeight: '1.55',
  					letterSpacing: '-0.006em'
  				}
  			],
  			caption: [
  				'0.75rem',
  				{
  					lineHeight: '1.5'
  				}
  			],
  			overline: [
  				'0.6875rem',
  				{
  					lineHeight: '1.4',
  					letterSpacing: '0.06em',
  					fontWeight: '600'
  				}
  			]
  		},
  		boxShadow: {
  			'elevation-xs': '0 1px 2px 0 rgb(18 18 28 / 0.04)',
  			'elevation-sm': '0 1px 3px 0 rgb(18 18 28 / 0.06), 0 1px 2px -1px rgb(18 18 28 / 0.05)',
  			'elevation-md': '0 4px 12px -2px rgb(18 18 28 / 0.08), 0 2px 6px -2px rgb(18 18 28 / 0.05)',
  			'elevation-lg': '0 12px 28px -6px rgb(18 18 28 / 0.10), 0 6px 12px -6px rgb(18 18 28 / 0.06)',
  			'elevation-xl': '0 24px 48px -12px rgb(18 18 28 / 0.14), 0 10px 20px -8px rgb(18 18 28 / 0.08)',
  			'elevation-2xl': '0 32px 64px -16px rgb(18 18 28 / 0.18)',
			'glow-subtle': '0 4px 16px -6px hsl(175 77% 26% / 0.18)',
			'glow-medium': '0 8px 24px -6px hsl(175 77% 26% / 0.28)',
			'glow-strong': '0 12px 32px -8px hsl(175 77% 26% / 0.40)',
			'glow-cyan': '0 8px 24px -6px hsl(175 77% 26% / 0.30)',
			'glow-blue': '0 8px 24px -6px hsl(186 70% 36% / 0.30)',
			'glow-violet': '0 8px 24px -6px hsl(168 55% 38% / 0.30)',
			'inner-glow-t': 'inset 0 1px 0 0 rgb(255 255 255 / 0.6)',
			'inner-glow-b': 'inset 0 -1px 0 0 rgb(18 18 28 / 0.04)',
			'inner-depth': 'inset 0 2px 6px 0 rgb(18 18 28 / 0.05)',
			card: '0 1px 3px 0 rgb(18 18 28 / 0.06), 0 1px 2px -1px rgb(18 18 28 / 0.05)',
			'card-hover': '0 12px 28px -6px rgb(18 18 28 / 0.12), 0 4px 10px -4px hsl(175 77% 26% / 0.10)',
			'card-active': 'inset 0 1px 3px 0 rgb(18 18 28 / 0.06)',
			'button-glow': '0 8px 24px -6px hsl(175 77% 26% / 0.35)',
			'button-glow-lg': '0 12px 32px -8px hsl(175 77% 26% / 0.45)'
  		},
  		keyframes: {
  			'fade-in-up': {
  				'0%': {
  					opacity: '0',
  					transform: 'translateY(12px)'
  				},
  				'100%': {
  					opacity: '1',
  					transform: 'translateY(0)'
  				}
  			},
  			'fade-in-scale': {
  				'0%': {
  					opacity: '0',
  					transform: 'scale(0.96)'
  				},
  				'100%': {
  					opacity: '1',
  					transform: 'scale(1)'
  				}
  			},
  			'slide-in-left': {
  				'0%': {
  					opacity: '0',
  					transform: 'translateX(-16px)'
  				},
  				'100%': {
  					opacity: '1',
  					transform: 'translateX(0)'
  				}
  			},
  			'slide-in-right': {
  				'0%': {
  					opacity: '0',
  					transform: 'translateX(16px)'
  				},
  				'100%': {
  					opacity: '1',
  					transform: 'translateX(0)'
  				}
  			},
  			'gradient-flow': {
  				'0%, 100%': {
  					backgroundPosition: '0% 50%'
  				},
  				'50%': {
  					backgroundPosition: '100% 50%'
  				}
  			},
			'glow-pulse': {
				'0%, 100%': {
					boxShadow: '0 0 0 0 hsl(175 77% 26% / 0)'
				},
				'50%': {
					boxShadow: '0 8px 24px -6px hsl(175 77% 26% / 0.30)'
				}
			},
  			'shimmer': {
  				'0%': {
  					backgroundPosition: '-200% 0'
  				},
  				'100%': {
  					backgroundPosition: '200% 0'
  				}
  			},
  			'progress-shimmer': {
  				'0%': {
  					transform: 'translateX(-100%)'
  				},
  				'100%': {
  					transform: 'translateX(200%)'
  				}
  			},
  			'pulse-slow': {
  				'0%, 100%': {
  					opacity: '1'
  				},
  				'50%': {
  					opacity: '0.6'
  				}
  			},
  			'accordion-down': {
  				from: {
  					height: '0'
  				},
  				to: {
  					height: 'var(--radix-accordion-content-height)'
  				}
  			},
  			'accordion-up': {
  				from: {
  					height: 'var(--radix-accordion-content-height)'
  				},
  				to: {
  					height: '0'
  				}
  			}
  		},
  		animation: {
  			'fade-in-up': 'fade-in-up 0.5s cubic-bezier(0.16, 1, 0.3, 1) both',
  			'fade-in-scale': 'fade-in-scale 0.4s cubic-bezier(0.16, 1, 0.3, 1) both',
  			'slide-in-left': 'slide-in-left 0.4s cubic-bezier(0.16, 1, 0.3, 1) both',
  			'slide-in-right': 'slide-in-right 0.4s cubic-bezier(0.16, 1, 0.3, 1) both',
  			'gradient-flow': 'gradient-flow 8s ease infinite',
  			'glow-pulse': 'glow-pulse 2.5s ease-in-out infinite',
  			'shimmer': 'shimmer 2s ease-in-out infinite',
  			'progress-shimmer': 'progress-shimmer 1.5s ease-in-out infinite',
  			'pulse-slow': 'pulse-slow 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
  			'accordion-down': 'accordion-down 0.2s ease-out',
  			'accordion-up': 'accordion-up 0.2s ease-out'
  		},
  		transitionTimingFunction: {
  			'out-expo': 'cubic-bezier(0.16, 1, 0.3, 1)',
  			'out-back': 'cubic-bezier(0.34, 1.56, 0.64, 1)',
  			'in-out': 'cubic-bezier(0.65, 0, 0.35, 1)',
  			spring: 'cubic-bezier(0.22, 1.2, 0.36, 1)'
  		},
  		backdropBlur: {
  			xs: '2px',
  			glass: '20px',
  			'glass-lg': '28px'
  		},
  		saturate: {
  			'150': '1.5',
  			'180': '1.8',
  			'200': '2'
  		}
  	}
  },
  plugins: [
    require("tailwindcss-animate"),
    function({ addUtilities }) {
      addUtilities({
        '.backdrop-glass': {
          'backdrop-filter': 'blur(20px) saturate(160%)',
          '-webkit-backdrop-filter': 'blur(20px) saturate(160%)',
        },
        '.backdrop-glass-lg': {
          'backdrop-filter': 'blur(28px) saturate(160%)',
          '-webkit-backdrop-filter': 'blur(28px) saturate(160%)',
        },
        '.bg-glass': {
          'background': 'hsl(var(--cosmic-surface) / 0.72)',
        },
        '.bg-glass-elevated': {
          'background': 'hsl(var(--cosmic-surface) / 0.85)',
        },
      })
    },
  ],
}
