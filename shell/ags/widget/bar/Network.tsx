import { createBinding } from "ags";
import AstalNetwork from "gi://AstalNetwork";

const network = AstalNetwork.get_default();

function netIcon(net: any): string {
    if (net.primary === AstalNetwork.Primary.WIRED) {
        return "network-wired-symbolic";
    }
    return net.wifi?.iconName ?? "network-offline-symbolic";
}

function netTooltip(net: any): string {
    if (net.primary === AstalNetwork.Primary.WIRED) return "Wired";
    const ssid = net.wifi?.ssid;
    return ssid ? `Wi-Fi: ${ssid}` : "Disconnected";
}

export function Network() {
    return (
        <image
            cssClasses={["Network"]}
            iconName={createBinding(network, "connectivity")(() => netIcon(network))}
            tooltipText={createBinding(network, "connectivity")(() => netTooltip(network))}
        />
    );
}
