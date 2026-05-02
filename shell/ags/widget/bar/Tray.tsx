import { For, createBinding } from "ags";
import AstalTray from "gi://AstalTray";

const tray = AstalTray.get_default();

function TrayItem({ item }: { item: any }) {
    return (
        <menubutton
            cssClasses={["Tray-item"]}
            tooltipMarkup={createBinding(item, "tooltipMarkup")}
            $={(self: any) => {
                self.menuModel = item.menuModel;
                self.insert_action_group("dbusmenu", item.actionGroup);
                item.connect("notify::action-group", () => {
                    self.insert_action_group("dbusmenu", item.actionGroup);
                });
            }}
        >
            <image gicon={createBinding(item, "gicon")} />
        </menubutton>
    );
}

export function Tray() {
    return (
        <box cssClasses={["Tray"]}>
            <For each={createBinding(tray, "items")}>
                {(item: any) => <TrayItem item={item} />}
            </For>
        </box>
    );
}
