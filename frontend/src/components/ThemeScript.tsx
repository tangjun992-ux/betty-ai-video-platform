/**
 * Inline script injected into <head> to prevent FOUC (flash of unstyled content)
 * on theme change. Runs before React hydrates to set the correct class.
 */
export function ThemeScript() {
  return (
    <script
      dangerouslySetInnerHTML={{
        __html: `
          (function() {
            try {
              var stored = localStorage.getItem('betty-theme');
              var theme = (stored === 'dark' || stored === 'light') ? stored : 'light';
              document.documentElement.classList.add(theme);
            } catch(e) {}
          })();
        `,
      }}
    />
  );
}
