/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_VIP_MODULE_ENABLED?: string;
  readonly VITE_ANALYTICS_ENABLED?: string;
  readonly DEV?: boolean;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
