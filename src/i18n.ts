import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import { buildI18nResources, SupportedLanguage } from './config/terminology';

const savedLanguage = (localStorage.getItem('evidentia_language') as SupportedLanguage) || 'en';

// Set document lang attribute for typography and line-height CSS rules
if (typeof document !== 'undefined') {
  document.documentElement.lang = savedLanguage;
  document.documentElement.setAttribute('translate', 'no');
  document.documentElement.classList.add('notranslate');
}

i18n
  .use(initReactI18next)
  .init({
    resources: buildI18nResources(),
    lng: savedLanguage,
    fallbackLng: 'en',
    interpolation: {
      escapeValue: false, // React already escapes values
    },
  });

export function setApplicationLanguage(lang: SupportedLanguage) {
  localStorage.setItem('evidentia_language', lang);
  i18n.changeLanguage(lang);
  if (typeof document !== 'undefined') {
    document.documentElement.lang = lang;
    document.documentElement.setAttribute('translate', 'no');
    document.documentElement.classList.add('notranslate');
  }
}

export function getApplicationLanguage(): SupportedLanguage {
  return (i18n.language as SupportedLanguage) || 'en';
}

export type { SupportedLanguage };
export default i18n;
