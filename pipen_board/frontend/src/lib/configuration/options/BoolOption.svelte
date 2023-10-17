<script>
    import Toggle from "carbon-components-svelte/src/Toggle/Toggle.svelte";
    import OptionFrame from "./OptionFrame.svelte";
    import { get_pgvalue } from "../../utils";
    import { storedGlobalChanged } from "../../store";

    export let key;
    export let value;
    export let readonly = false;
    export let pgargs = {};
    export let pgargkey = null;
    export let changed = false;

    if (typeof value === "string") {
        value = ["true", "yes", "on", "1"].includes(value.toLowerCase());
    }

    const pgvalue = get_pgvalue(pgargs, pgargkey === true ? key : pgargkey);
    $: if (pgvalue !== undefined && !changed) {
        value = pgvalue;
    }
</script>

<OptionFrame on:mouseenter on:mouseleave>
    <div
        slot="label"
        style='--pgarg: "This option is linked to Group Argument: {pgargkey === true ? key : pgargkey}"'
        class='{readonly ? "readonly-label" : ""} {pgargkey ? "linked-pgarg-label" : ""}'>{key}</div>
    <div slot="field" style="align-self: center;">
        <Toggle
            on:focus
            on:blur
            {readonly}
            on:toggle={e => { changed = true; storedGlobalChanged.set(true); if (readonly) value = !e.detail.toggled} }
            size="sm"
            labelText={key}
            bind:toggled={value}
            hideLabel
        />
    </div>
</OptionFrame>
