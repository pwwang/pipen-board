<script>
    import { createEventDispatcher, onMount } from "svelte";
    import Dropdown from "carbon-components-svelte/src/Dropdown/Dropdown.svelte";
    import OptionFrame from "./OptionFrame.svelte";
    import { validateData, get_pgvalue } from "../../utils";
    import { removeError, setError, storedGlobalChanged } from "../../store";

    export let key;
    export let value;
    export let choices;
    export let choicesDesc;
    export let activeNavItem;
    export let required = false;
    export let readonly = false;
    export let pgargs = {};
    export let pgargkey = null;
    export let changed = false;

    let button = null;
    let selectedId = choices.indexOf(value);
    let origSelectedId = selectedId;
    let invalid = false;
    let invalidText = "";
    let dispatch = createEventDispatcher();

    const fmtItem = (item) => {
        const desc = choicesDesc ? choicesDesc[item.id] : null;
        return desc ? `${item.text}: ${desc}` : item.text;
    };

    const validateValue = (sid) => {
        if (sid !== -1 || !required) {
            invalid = false;
            removeError(`${activeNavItem} / ${key}`);
            return;
        }
        const error = validateData(undefined, ["required"]);
        invalid = error !== null;
        invalidText = error;
        if (invalid) {
            setError(`${activeNavItem} / ${key}`, invalidText);
        } else {
            removeError(`${activeNavItem} / ${key}`);
        }
    };

    // Change the value and pass it to the parent component
    $: value = choices[selectedId];
    const pgvalue = get_pgvalue(pgargs, pgargkey === true ? key : pgargkey);
    $: if (pgvalue !== undefined && !changed) {
        selectedId = choices.indexOf(pgvalue);
    }

    onMount(() => {
        button.onfocus = () => {
            dispatch("focus");
        };
        button.onblur = () => {
            dispatch("blur");
        };

        validateValue(selectedId);
    });
</script>

<OptionFrame on:mouseenter on:mouseleave>
    <div
        slot="label"
        style='--pgarg: "This option is linked to Group Argument: {pgargkey === true ? key : pgargkey}"'
        class='{readonly ? "readonly-label" : ""} {pgargkey ? "linked-pgarg-label" : ""}'>{key}</div>
    <div slot="field">
        <Dropdown
            itemToString={fmtItem}
            size="sm"
            titleText={key}
            hideLabel
            {invalid}
            {invalidText}
            label="Select an option"
            bind:selectedId
            bind:ref={button}
            on:select={e => {
                changed = true;
                storedGlobalChanged.set(true);
                if (readonly)  {selectedId = origSelectedId;}
                validateValue(selectedId);
            }}
            items={choices.map((choice) => ({
                id: choices.indexOf(choice),
                text: choice,
            }))}
        />
    </div>
</OptionFrame>
