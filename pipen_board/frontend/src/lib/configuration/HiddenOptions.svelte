<script>
    import InlineNotification from "carbon-components-svelte/src/Notification/InlineNotification.svelte";

    export let description;
    export let initDescription = undefined;

    if (initDescription) {
        description = initDescription;
    }
</script>

<div class="center-wrapper">
    <InlineNotification
        lowContrast
        kind="warning"
        hideCloseButton
    >This process is not allowed for configuration</InlineNotification>
</div>
