import { createBinding } from "ags";
import Wp from "gi://AstalWp";

const wp = Wp.get_default();
const speaker = wp?.audio?.defaultSpeaker;

function iconForVolume(volume: number, muted: boolean): string {
    if (muted) return "audio-volume-muted-symbolic";
    if (volume <= 0)   return "audio-volume-muted-symbolic";
    if (volume < 0.34) return "audio-volume-low-symbolic";
    if (volume < 0.67) return "audio-volume-medium-symbolic";
    return "audio-volume-high-symbolic";
}

export function Audio() {
    if (!speaker) {
        return <box cssClasses={["Audio", "missing"]} />;
    }

    return (
        <button
            cssClasses={["Audio"]}
            tooltipText={createBinding(speaker, "volume")((v) => `Volume ${Math.round(v * 100)}%`)}
            onClicked={() => speaker.set_mute(!speaker.mute)}
        >
            <image
                iconName={createBinding(speaker, "volume")((v) =>
                    iconForVolume(v, speaker.mute),
                )}
            />
        </button>
    );
}
