import { createPoll } from "ags/time";

export function Clock() {
    const time = createPoll("", 1000, "date", ["+%H:%M"]);
    const date = createPoll("", 60_000, "date", ["+%a %d %b"]);

    return (
        <box cssClasses={["Clock"]}>
            <label cssClasses={["Clock-time"]} label={time} />
            <label cssClasses={["Clock-date"]} label={date} />
        </box>
    );
}
