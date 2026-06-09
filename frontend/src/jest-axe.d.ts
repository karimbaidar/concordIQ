// Minimal local types for jest-axe (no @types/jest-axe dependency needed).
declare module "jest-axe" {
  export interface AxeViolation {
    id: string;
    impact?: "minor" | "moderate" | "serious" | "critical" | null;
    description?: string;
    help?: string;
    nodes?: unknown[];
  }
  export interface AxeResults {
    violations: AxeViolation[];
    passes: unknown[];
    incomplete: unknown[];
  }
  export function axe(html: Element | string, options?: unknown): Promise<AxeResults>;
}
