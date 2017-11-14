var submitting = false;

function submitForm(form) {
    $('form .form-group').find('div.errors').remove();
    submitting = true;
    var formData = new FormData(form);
    $.ajax({
        url: '/api/v2/core/formstorages/?format=json',
        type: 'post',
        data: formData,
        contentType: false,
        processData: false,
        headers: {
            'X-CSRFToken': $('input[name=csrfmiddlewaretoken]').val()
        },
        success: function (response) {
            $(form).html('<div class="alert alert-success" role="alert">' + response.message + '</div>')
            submitting = false;
        },
        error: function (response) {
            for (var field in response.responseJSON) {
                var errorElem;
                if ($('form .form-group.field-' + field).find('[name=' + field + ']').length === 0)
                    continue
                errorElem = $('form .form-group.field-' + field).find('div.errors');

                console.log(field, errorElem);

                if (errorElem.length === 0) {
                    console.log('added to', $('form .form-group.field-' + field));
                    errorElem = $('<div class="errors"></div>');
                    $('form .form-group.field-' + field).children('label').after(errorElem);
                }
                var errors = response.responseJSON[field].map(function (elem) {
                    return '<p class="label label-danger">' + elem + '</p>'
                }).join('');
                errorElem.html(errors);
            }
            submitting = true;
        }
    });
    return false;

}

jQuery(function ($) {
    var formRenderOpts = {
            dataType: 'json',
            formData: $('#form-builder').data('config')
        },
        renderedForm = $('<div>');
    renderedForm.formRender(formRenderOpts);
    var htmlForm = $(renderedForm.html());
    $(htmlForm).find('input[type=date]').attr({type: 'text'}).addClass('datapicker');
    $(htmlForm).find('select').each(function () {
        var elemName = $(this).attr('name');
        if (elemName.indexOf('[]') === elemName.length - 2)
            $(this).attr('name', elemName.split('').splice(0, elemName.length - 2).join(''));
    });
    $('#form-builder').html(htmlForm.html());
    $(".datapicker").datepicker();
});