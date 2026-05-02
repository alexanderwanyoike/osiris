import app from "ags/gtk4/app";
import { Astal, Gdk, Gtk } from "ags/gtk4";

import { Workspaces } from "./Workspaces";
import { Audio }      from "./Audio";
import { Network }    from "./Network";
import { Battery }    from "./Battery";
import { Clock }      from "./Clock";
import { Tray }       from "./Tray";

interface BarProps {
    gdkmonitor: Gdk.Monitor;
}

export function Bar({ gdkmonitor }: BarProps) {
    const { TOP, LEFT, RIGHT } = Astal.WindowAnchor;

    return (
        <window
            visible
            name="osiris-bar"
            namespace="osiris-bar"
            cssClasses={["Bar"]}
            gdkmonitor={gdkmonitor}
            exclusivity={Astal.Exclusivity.EXCLUSIVE}
            application={app}
            anchor={TOP | LEFT | RIGHT}
        >
            <centerbox cssClasses={["Bar-inner"]}>
                <box hexpand halign={Gtk.Align.START} $type="start">
                    <Workspaces />
                </box>
                <box halign={Gtk.Align.CENTER} $type="center">
                    <Clock />
                </box>
                <box hexpand halign={Gtk.Align.END} $type="end">
                    <Tray />
                    <Audio />
                    <Network />
                    <Battery />
                </box>
            </centerbox>
        </window>
    );
}
