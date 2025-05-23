(function() {
    const textareas = document.querySelectorAll("textarea[data-jsonwidget]");
    textareas.forEach(function(textarea) {
        const widgetId = textarea.getAttribute("id").replace(/_textarea$/, "")
        const widgetName = textarea.getAttribute("name")
        const container = document.getElementById(widgetId);
        const options = {
            modes: ['text', 'code', 'tree', 'form', 'view'],
            mode: 'code',
            search: true,
            onChange: function () {
                var json = editor.get();
                textarea.value = JSON.stringify(json);
            }
        }

        const editor = new JSONEditor(container, options);
        const content = document.getElementById(`${widgetName}_data`).textContent;
        textarea.value = content;
        editor.set(JSON.parse(content));
    });
})();
