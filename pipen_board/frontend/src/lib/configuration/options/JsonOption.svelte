<script>
// @ts-nocheck

    import { onMount } from "svelte";
    import TextArea from "carbon-components-svelte/src/TextArea/TextArea.svelte";
    import OptionFrame from "./OptionFrame.svelte";
    import { validateData, autoHeight, insertTab } from "../../utils";

    export let key;
    export let value;
    export let placeholder;
    export let required = false;
    export let activeNavItem;
    export let readonly = false;
    export let setError;
    export let removeError;

    let validator = ["json"];
    let invalid = false;
    let invalidText = "";
    let strValue = value;
    let origValue = value;
    let textarea = null;
    if (value && typeof value === "object") {
        strValue = JSON.stringify(value, null, 2);
    }

    if (required) {
        validator = ["required", ...validator]
    }

    const validateValue = (v, onmount = false) => {
        if (
            (origValue === null || origValue === undefined)
            && (v === "" || v === null || v === undefined)
        ) {
            value = origValue;
            return;
        }
        const error = validateData(v, validator);
        invalid = error !== null;
        invalidText = error;
        if (invalid) {
            setError(`${activeNavItem} / ${key}`, invalidText);
            // keep it
            value = v;
        } else {
            removeError(`${activeNavItem} / ${key}`);
            if (!onmount) {
                value = JSON.parse(v);
            }
        }
        autoHeight(textarea);
    };

    onMount(() => {
        if (!readonly) {
            validateValue(strValue, true);
        }
    });
</script>

<OptionFrame on:mouseenter on:mouseleave>
    <div slot="label">{key} {readonly ? '(readonly)' : ''}</div>
    <div slot="field">
        <TextArea
            on:focus
            on:blur
            on:input={e => validateValue(e.target.value)}
            on:keydown={insertTab}
            {invalid}
            {invalidText}
            {readonly}
            {placeholder}
            labelText={key}
            hideLabel
            rows={1}
            bind:value={strValue}
            bind:ref={textarea}
        />
    </div>
</OptionFrame>
