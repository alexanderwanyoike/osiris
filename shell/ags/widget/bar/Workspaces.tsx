import { For, createBinding } from "ags";
import Hyprland from "gi://AstalHyprland";

const hypr = Hyprland.get_default();

export function Workspaces() {
    return (
        <box cssClasses={["Workspaces"]}>
            <For each={createBinding(hypr, "workspaces")}>
                {(ws) => (
                    <button
                        cssClasses={createBinding(hypr, "focusedWorkspace")((focused) =>
                            focused?.id === ws.id ? ["ws", "focused"] : ["ws"],
                        )}
                        onClicked={() => ws.focus()}
                    >
                        <label label={String(ws.id)} />
                    </button>
                )}
            </For>
        </box>
    );
}
