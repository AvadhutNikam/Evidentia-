// Re-export all navigation config types, groups and items from caseNav.ts
export * from './caseNav';
export { CASE_NAV_GROUPS as CASE_NAVIGATION_GROUPS } from './caseNav';
export { SETTINGS_TECHNICAL_ITEMS as ADMIN_SETTINGS_ITEMS } from './caseNav';
export type { CaseNavItem as NavItemConfig, CaseNavGroup as NavGroupConfig } from './caseNav';
