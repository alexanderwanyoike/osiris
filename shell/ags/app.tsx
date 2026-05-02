// Osiris shell entrypoint.
// Launches the bar on every monitor, mounts notifications and launcher windows.

import app from "ags/gtk4/app";
import { exec } from "ags/process";
import { For, createBinding } from "ags";
import { Gdk } from "ags/gtk4";
import GLib from "gi://GLib?version=2.0";

import { themeToCss } from "./lib/theme";
import { Bar } from "./widget/bar";

const userConfig = GLib.get_user_config_dir();
const scssPath   = `${userConfig}/ags/style/main.scss`;
const cssPath    = `${userConfig}/ags/style/main.css`;
const themeCssPath = `${userConfig}/ags/style/theme.css`;

function writeThemeCss(): void {
    GLib.file_set_contents(themeCssPath, themeToCss());
}

function compileScss(): void {
    try {
        exec(`sass ${scssPath} ${cssPath}`);
    } catch (err) {
        console.error("sass compile failed:", err);
    }
}

app.start({
    instanceName: "osiris",
    css: cssPath,

    main() {
        writeThemeCss();
        compileScss();

        const monitors = createBinding(app, "monitors");
        return (
            <For each={monitors} cleanup={(win: any) => win?.destroy?.()}>
                {(monitor: Gdk.Monitor) => <Bar gdkmonitor={monitor} />}
            </For>
        );
    },
});
