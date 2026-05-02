// Osiris shell theme tokens.
//
// This file is the source of truth for colors, spacing, radius and typography
// across the desktop shell. It is intentionally flat and free of logic so the
// AI agent can rewrite it (or generate alternatives) reliably.
//
// SCSS in shell/ags/style/ consumes these tokens via CSS custom properties
// emitted by themeToCss() at startup.

export const colors = {
    background:      "#0d0d10",
    surface:         "#1a1a1f",
    surfaceMuted:    "#2a2a2f",
    border:          "#2a2a2a",
    borderActive:    "#7c8aeb",
    foreground:      "#e8e8e8",
    foregroundMuted: "#a0a0a8",
    accent:          "#7c8aeb",
    accentMuted:     "#5560a8",
    success:         "#98c379",
    warning:         "#e5c07b",
    danger:          "#e06c75",
} as const;

export const spacing = {
    xs: 4,
    sm: 8,
    md: 12,
    lg: 16,
    xl: 24,
} as const;

export const radius = {
    sm: 4,
    md: 8,
    lg: 12,
} as const;

export const typography = {
    fontFamily:   "Inter, system-ui, sans-serif",
    fontFamilyMono: "monospace",
    fontSizeSm:   11,
    fontSizeMd:   13,
    fontSizeLg:   16,
} as const;

export type Theme = {
    colors:     typeof colors;
    spacing:    typeof spacing;
    radius:     typeof radius;
    typography: typeof typography;
};

export const theme: Theme = { colors, spacing, radius, typography };

const kebab = (s: string): string =>
    s.replace(/[A-Z]/g, (m) => "-" + m.toLowerCase());

/** Render the theme as a `:root { --osiris-* }` CSS block for injection. */
export function themeToCss(t: Theme = theme): string {
    const lines: string[] = [];
    for (const [k, v] of Object.entries(t.colors)) {
        lines.push(`  --osiris-color-${kebab(k)}: ${v};`);
    }
    for (const [k, v] of Object.entries(t.spacing)) {
        lines.push(`  --osiris-spacing-${k}: ${v}px;`);
    }
    for (const [k, v] of Object.entries(t.radius)) {
        lines.push(`  --osiris-radius-${k}: ${v}px;`);
    }
    lines.push(`  --osiris-font-family: ${t.typography.fontFamily};`);
    lines.push(`  --osiris-font-family-mono: ${t.typography.fontFamilyMono};`);
    lines.push(`  --osiris-font-size-sm: ${t.typography.fontSizeSm}px;`);
    lines.push(`  --osiris-font-size-md: ${t.typography.fontSizeMd}px;`);
    lines.push(`  --osiris-font-size-lg: ${t.typography.fontSizeLg}px;`);
    return `:root {\n${lines.join("\n")}\n}\n`;
}
