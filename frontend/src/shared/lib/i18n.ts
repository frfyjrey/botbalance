import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import { STORAGE_KEYS, LANGUAGES } from '@shared/config/constants';

// Import translation files
import enCommon from '../../locales/en/common.json';
import enAuth from '../../locales/en/auth.json';
import enDashboard from '../../locales/en/dashboard.json';

import ruCommon from '../../locales/ru/common.json';
import ruAuth from '../../locales/ru/auth.json';
import ruDashboard from '../../locales/ru/dashboard.json';

const resources = {
  en: {
    common: enCommon,
    auth: enAuth,
    dashboard: enDashboard,
  },
  ru: {
    common: ruCommon,
    auth: ruAuth,
    dashboard: ruDashboard,
  },
};

i18n.use(initReactI18next).init({
  resources,
  lng: LANGUAGES.RU, // По умолчанию русский
  fallbackLng: LANGUAGES.EN,
  defaultNS: 'common',
  ns: ['common', 'auth', 'dashboard'],

  interpolation: {
    escapeValue: false,
  },

  react: {
    useSuspense: false,
  },
});

// Save language to localStorage when changed
i18n.on('languageChanged', lng => {
  localStorage.setItem(STORAGE_KEYS.LANGUAGE, lng);
});

export default i18n;
