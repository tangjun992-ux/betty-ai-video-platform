/** Apply persisted language before hydration to avoid a lang-attribute flash. */
export function LocaleScript() {
  return (
    <script
      dangerouslySetInnerHTML={{
        __html: `(function(){try{var l=localStorage.getItem('betty-locale');document.documentElement.lang=l==='en'?'en':'zh-CN'}catch(e){}})();`,
      }}
    />
  );
}
