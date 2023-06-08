<script>
    import Toggle from "carbon-components-svelte/src/Toggle/Toggle.svelte";
    import OptionFrame from "./OptionFrame.svelte";
    import { get_pgvalue } from "../../utils";

    export let key;
    export let value;
    export let readonly = false;
    export let pgargs = {};
    export let pgargkey = null;
    export let changed = false;

    if (typeof value === "string") {
        value = ["true", "yes", "on", "1"].includes(value.toLowerCase());
    }

    $: pgvalue = get_pgvalue(pgargs, pgargkey === true ? key : pgargkey);
    $: if (pgvalue !== undefined && !changed) {
        value = pgvalue;
    }
</script>

<OptionFrame on:mouseenter on:mouseleave>
    <div slot="label" style="height: 1.2rem;" class={readonly ? "readonly-label" : ""}>{key}</div>
    <div slot="field" style="align-self: center;">
        <Toggle
            on:focus
            on:blur
            {readonly}
            on:toggle={e => { changed = true; if (readonly) value = !e.detail.toggled} }
            size="sm"
            labelText={key}
            bind:toggled={value}
            hideLabel
        />
    </div>
</OptionFrame>
