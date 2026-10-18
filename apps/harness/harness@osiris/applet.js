// The panel button for the Harness: the same toggle as Super+A.

const Applet = imports.ui.applet;
const Util = imports.misc.util;

class HarnessApplet extends Applet.IconApplet {
    constructor(orientation, panelHeight, instanceId) {
        super(orientation, panelHeight, instanceId);
        this.set_applet_icon_symbolic_name('sidebar-show-right-symbolic');
        this.set_applet_tooltip('Harness (Super+A)');
    }

    on_applet_clicked(event) {
        Util.spawn(['gapplication', 'action', 'dev.osiris.Harness', 'show']);
    }
}

function main(metadata, orientation, panelHeight, instanceId) {
    return new HarnessApplet(orientation, panelHeight, instanceId);
}
