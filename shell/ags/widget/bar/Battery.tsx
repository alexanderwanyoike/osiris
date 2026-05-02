import { createBinding } from "ags";
import AstalBattery from "gi://AstalBattery";

const battery = AstalBattery.get_default();

export function Battery() {
    return (
        <image
            cssClasses={["Battery"]}
            visible={createBinding(battery, "isBattery")}
            iconName={createBinding(battery, "batteryIconName")}
            tooltipText={createBinding(battery, "percentage")(
                (p) => `${Math.round(p * 100)}%`,
            )}
        />
    );
}
