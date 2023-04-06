<script>
    import { onMount } from "svelte";
    import MultiSelect from "carbon-components-svelte/src/MultiSelect/MultiSelect.svelte";
    import OptionFrame from "./OptionFrame.svelte";

    export let key;
    export let value;
    export let choices;
    export let choicesDesc;
    export let required = false;
    export let activeNavItem;
    export let readonly = false;
    export let setError;
    export let removeError;

    let invalid = false;
    let invalidText = "";

    if (!value) {
        value = [];
    }

    let selectedIds = value.map((v) => choices.indexOf(v));
    let origSelectedIds = selectedIds;

    const fmtItem = (item) => {
        const desc = choicesDesc ? choicesDesc[item.id] : null;
        return desc ? `${item.text}: ${desc}` : item.text;
    };

    const validateValue = (v) => {
        value = v.map((i) => choices[i]);
        if (required && value.length === 0) {
            invalid = true;
            invalidText = "At least one choice must be selected.";
            setError(`${activeNavItem} / ${key}`, invalidText);
        } else {
            invalid = false;
            invalidText = "";
            removeError(`${activeNavItem} / ${key}`);
        }
    };

    onMount(() => {
        if (!readonly) {
            validateValue(selectedIds);
        }
    });
</script>

<OptionFrame on:mouseenter on:mouseleave>
    <div slot="label">{key} {readonly ? '(readonly)' : ''}</div>
    <div slot="field">
        <MultiSelect
            on:blur
            on:focus
            filterable
            filterItem={(item, value) => fmtItem(item).toLowerCase().includes(value.trim().toLowerCase())}
            size="sm"
            titleText={key}
            hideLabel
            {invalid}
            {invalidText}
            bind:selectedIds
            on:select={(e) => {
                if (readonly) { selectedIds = origSelectedIds; }
                else { validateValue(e.detail.selectedIds); }
            } }
            items={choices.map((choice) => ({
                id: choices.indexOf(choice),
                text: choice.toString(),
            }))}
            let:item
        >
            <div title={fmtItem(item)} class="ms-item">{fmtItem(item)}</div>
        </MultiSelect>
    </div>
</OptionFrame>

<style>
    .ms-item {
        display: inline-block;
        width: 100%;
    }
</style>
