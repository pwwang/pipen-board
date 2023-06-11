<script>
    import { onMount } from "svelte";
    import MultiSelect from "carbon-components-svelte/src/MultiSelect/MultiSelect.svelte";
    import OptionFrame from "./OptionFrame.svelte";
    import { get_pgvalue } from "../../utils";

    export let key;
    export let value;
    export let choices;
    export let choicesDesc;
    export let required = false;
    export let activeNavItem;
    export let readonly = false;
    export let setError;
    export let removeError;
    export let pgargs = {};
    export let pgargkey = null;
    // Note that unlike other options, on:select/on:change is not
    // appropriate. So we use on:focus instead.
    export let changed = false;

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

    $: pgvalue = JSON.stringify(get_pgvalue(pgargs, pgargkey === true ? key : pgargkey));
    $: if (pgvalue !== undefined && !changed) {
        const pgv = JSON.parse(pgvalue);
        selectedIds = pgv.map((v) => choices.indexOf(v));
        // Change of selectedIds will trigger validateValue as
        // the event on:select is triggered.
        // value = selectedIds.map((i) => choices[i]);
    }

    onMount(() => {
        if (!readonly) {
            validateValue(selectedIds);
        }
    });
</script>

<OptionFrame on:mouseenter on:mouseleave>
    <div
        slot="label"
        style='--pgarg: "This option is linked to Group Argument: {pgargkey === true ? key : pgargkey}"'
        class='{readonly ? "readonly-label" : ""}{pgargkey ? "linked-pgarg-label" : ""}'>{key}</div>
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
            on:focus={() => { changed = true; }}
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
