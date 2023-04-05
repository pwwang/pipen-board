<script>
    import Toggle from "carbon-components-svelte/src/Toggle/Toggle.svelte";
    import OptionFrame from "./OptionFrame.svelte";

    export let key;
    export let value;
    export let readonly = false;

    if (typeof value === "string") {
        value = ["true", "yes", "on", "1"].includes(value.toLowerCase());
    }
</script>

<OptionFrame on:mouseenter on:mouseleave>
    <div slot="label" style="height: 1.2rem;">{key} {readonly ? '(readonly)' : ''}</div>
    <div slot="field" style="align-self: center;">
        <Toggle
            on:focus
            on:blur
            {readonly}
            on:toggle={e => { if (readonly) value = !e.detail.toggled} }
            size="sm"
            labelText={key}
            bind:toggled={value}
            hideLabel
        />
    </div>
</OptionFrame>
