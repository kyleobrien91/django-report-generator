// place this in your static files folder, in:
//    <static>/report_builder/js/report_form.js

// initialize path prefix.
path_prefix = ""

// get current path
current_path =  window.location.pathname;

// where is "/report_builder"?
root_index = current_path.indexOf( "/report_builder" );

// other than 0?
if ( root_index > 0 )
{
    // yes.  Get all text from start to that location, store it as path_prefix.
    path_prefix = current_path.substring( 0, root_index );
}
else
{
    // no - set path_prefix to "".
    path_prefix = "";
}

var check_report = false;
function check_if_report_done(report_id, task_id) {
	if (check_report != false ){
		$.get( "/report_builder/report/"+ report_id + "/check_status/" + task_id + "/", function( data ) {
			console.log(data);
			if (data.state == "SUCCESS") {
				window.location.href = data.link;
				clearInterval(check_report);
				check_report = false;
			}
		})
	}
}
function get_async_report(report_id) {
	$.get( "/report_builder/report/"+ report_id + "/download_xlsx/", function( data ) {
	var task_id = data.task_id;
	status = "loading"
	check_report = setInterval( function(){ check_if_report_done(report_id, task_id); }, 2000 );
    });
}

function expand_related(event, model, field, path, path_verbose) {
    if (event.target.tagName != 'LI') return;

    var element = $(event.target);

    if ( $(element).hasClass('tree_closed') ){
        expanded_elements = [];

        $('li.tree_expanded').each(function(){
            expanded_elements.push($(this).data('model-id'));
        });

        $.get(
            path_prefix + "/report_builder/ajax_get_related/",  
            {model: model, field: field, path: path, path_verbose: path_verbose, exclude: expanded_elements},
            function(data){
                $(element).addClass('tree_expanded');
                $(element).removeClass('tree_closed');
                $(element).after('<li>' + data + '</li>');
            }  
        );
    } else{
        $(element).addClass('tree_closed');
        $(element).removeClass('tree_expanded');
        $(element).next().remove();
    }
}

function show_fields(event, model, field, path, path_verbose){
    $('.highlight').removeClass('highlight');
    $(event.target).addClass('highlight');
    $.get(  
        path_prefix + "/report_builder/ajax_get_fields/",  
        {model: model, field: field, path: path, path_verbose: path_verbose},
        function(data){
            $('#field_selection_div').html(data);
            
            enable_drag();
        }  
    );
}

function enable_drag() {
    $( ".draggable" ).draggable({
        connectToSortable: "#sortable",
        helper: "clone",
        revert: "invalid",
        zIndex: 10000
    });
    $( "#field_list_droppable" ).droppable({
        drop: function( event, ui ) {
            field = $.trim($(ui.draggable).text());
            name = $.trim($(ui.draggable).children().data('name'));
            label = $.trim($(ui.draggable).children().data('label'));
            path_verbose = $.trim($(ui.draggable).children().data('path_verbose'));
            path = $.trim($(ui.draggable).children().data('path'));
            
            if (name == '') return;
            
            total_forms = $('#id_displayfield_set-TOTAL_FORMS');
            i = total_forms.val();
            total_forms.val(parseInt(i)+1);
            
            row_html = '<tr><td><span style="cursor: move;" class="ui-icon ui-icon-arrowthick-2-n-s"></span></td>';
            row_html += '<td><input type="checkbox" name="displayfield_set-'+i+'-DELETE" id="id_displayfield_set-'+i+'-DELETE">';
            row_html += '<td>'+field+'<input id="id_displayfield_set-'+i+'-path_verbose" name="displayfield_set-'+i+'-path_verbose" readonly="readonly" type="hidden" value="' + path_verbose + '"/>';
            row_html += '<input id="id_displayfield_set-'+i+'-field_verbose" name="displayfield_set-'+i+'-field_verbose" readonly="readonly" type="hidden" value="' + field + '"/><input id="id_displayfield_set-'+i+'-path" name="displayfield_set-'+i+'-path" type="hidden" value="' + path + '"/></td>';
            row_html += '<td><input id="id_displayfield_set-'+i+'-field" name="displayfield_set-'+i+'-field" type="hidden" value="' + label + '"/>'
            row_html += '<input id="id_displayfield_set-'+i+'-name" name="displayfield_set-'+i+'-name" type="text" value="' + name + '"/></td>';
            row_html += '<td><input type="text" name="displayfield_set-'+i+'-sort" class="small_input" id="id_displayfield_set-'+i+'-sort">';
            row_html += '<input type="checkbox" name="displayfield_set-'+i+'-sort_reverse" id="id_displayfield_set-'+i+'-sort_reverse"></td>';
            row_html += '<td><input type="text" name="displayfield_set-'+i+'-width" class="small_input" value="15" id="id_displayfield_set-'+i+'-width"></td>';
            if ( field.indexOf("[custom") == -1 && field.indexOf("[property") == -1 ) {
                row_html += '<td onclick="aggregate_tip(event)"><select id="id_displayfield_set-'+i+'-aggregate" name="displayfield_set-'+i+'-aggregate"><option selected="selected" value="">---------</option><option value="Sum">Sum</option><option value="Count">Count</option><option value="Avg">Avg</option><option value="Max">Max</option><option value="Min">Min</option></select></td>';
            } else {
                row_html += '<td></td>'
            }
            row_html += '<td><select id="id_displayfield_set-'+i+'-display_format" name="displayfield_set-'+i+'-display_format"> /* populate options from DB on drop */ </select></td>';
            row_html += '<td><input type="checkbox" class="small_input" name="displayfield_set-'+i+'-total" id="id_displayfield_set-'+i+'-total"></td>';
            row_html += '<td><input type="checkbox" name="displayfield_set-'+i+'-group" id="id_displayfield_set-'+i+'-group">';
            row_html += '<span class="hide_me"><input type="text" name="displayfield_set-'+i+'-position" value="'+total_forms.val()+'" id="id_displayfield_set-'+i+'-position"></span></td>';
            row_html += '</tr>';
            $('#field_list_table > tbody:last').append(row_html);

            get_formats($('#'+'id_displayfield_set-'+i+'-display_format'));

        }

    });


    $("span.button[data-choices='true']").mousedown(function() {
        $.get( path_prefix + '/report_builder/ajax_get_choices/', {
            'path_verbose': $(this).data('path_verbose'),
            'path': $(this).data('path'),
            'app_label': $(this).data('app_label'),
            'label': $(this).data('label'),
            'root_model': $(this).data('root_model'),
            },
            function(data) {
                $("span.button[data-choices='true']").data('choices', data);
            }
        );
    });


    function get_formats(select) { 
        $(select).load( path_prefix + '/report_builder/ajax_get_formats/' );
    }


    $("#field_filter_droppable" ).droppable({
        drop: function( event, ui ) {
            field = $.trim($(ui.draggable).text());
            name = $.trim($(ui.draggable).children().data('name'));
            label = $.trim($(ui.draggable).children().data('label'));
            path_verbose = $.trim($(ui.draggable).children().data('path_verbose'));
            path = $.trim($(ui.draggable).children().data('path'));
            choices = $.trim($(ui.draggable).children().data('choices'));
            filter_field_pk = $.trim($(ui.draggable).children().data('pk'));

            if (field.match(/\[property\]/)) {
                property_tip();
            };
            
            if (name == '') return;
            
            total_forms = $('#id_fil-TOTAL_FORMS');
            i = total_forms.val();
            total_forms.val(parseInt(i)+1);
            
            row_html = '<tr>'
            row_html += '<td><span style="cursor: move;" class="ui-icon ui-icon-arrowthick-2-n-s"></span></td>'
            row_html += '<td><input type="checkbox" name="fil-'+i+'-DELETE" id="id_fil-'+i+'-DELETE">'
            row_html += '<span class="hide_me"><input type="text" name="fil-'+i+'-position" value="0" id="id_fil-'+i+'-position"></span>'
            row_html += '<input id="id_fil-'+i+'-path_verbose" value="'+ path_verbose +'" readonly="readonly" type="hidden" name="fil-'+i+'-path_verbose" maxlength="2000"></td>'
            row_html += '<td><input type="hidden" name="fil-'+i+'-field" value="'+ label +'" id="id_fil-'+i+'-field">'
            row_html += '<input name="fil-'+i+'-field_verbose" value="'+ field +'" readonly="readonly" maxlength="2000" type="text" id="id_fil-'+i+'-field_verbose">'
            row_html += '<input type="hidden" value="'+ path +'" name="fil-'+i+'-path" id="id_fil-'+i+'-path"></td>'
            row_html += '<td><select onchange="check_filter_type(event.target)" name="fil-'+i+'-filter_type" id="id_fil-'+i+'-filter_type">'
            row_html += '<option value="">---------</option>\
<option value="exact">Equals</option>\
<option value="iexact">Equals (case-insensitive)</option>\
<option value="contains">Contains</option>\
<option value="icontains" selected="selected">Contains (case-insensitive)</option>\
<option value="in">in (comma seperated 1,2,3)</option>\
<option value="gt">Greater than</option>\
<option value="gte">Greater than equals</option>\
<option value="lt">Less than</option>\
<option value="lte">Less than equals</option>\
<option value="startswith">Starts with</option>\
<option value="istartswith">Starts with (case-insensitive)</option>\
<option value="endswith">Ends with</option>\
<option value="iendswith">Ends with  (case-insensitive)</option>\
<option value="range">range</option>\
<option value="week_day">Week day</option>\
<option value="isnull">Is null</option>\
<option value="regex">Regular Expression</option>\
<option value="iregex">Reg. Exp. (case-insensitive)</option>\
</select></td>'
            if ( field.indexOf("DateField") > 0 ) {
            	row_html += '<td><input class="datepicker" id="id_fil-'+i+'-filter_value" type="text" name="fil-'+i+'-filter_value" value="" maxlength="2000"><input class="datepicker" id="id_fil-'+i+'-filter_value2" style="display: none;" type="text" name="fil-'+i+'-filter_value2" value="" maxlength="2000"></td>'
            } else if (choices) {
                row_html += '<td><select id="id_fil-'+i+'-filter_value" name="fil-'+i+'-filter_value">'+choices+'</select></td>'
            } else {
                row_html += '<td><input id="id_fil-'+i+'-filter_value" type="text" name="fil-'+i+'-filter_value" value="" maxlength="2000"><input id="id_fil-'+i+'-filter_value2" style="display: none;" type="text" name="fil-'+i+'-filter_value2" value="" maxlength="2000"></td>'
            }
            row_html += '<td><input type="checkbox" name="fil-'+i+'-exclude" id="id_fil-'+i+'-exclude"></td>'
            row_html += '</tr>'
            $('#field_filter_table > tbody:last').append(row_html);
            $( ".datepicker" ).datepicker();
        }
    });
}

function check_filter_type(element){
    var element = $(element);
    selected_type = element.find(":selected").val();
    element.closest('tr').find('input[name=check_value]').remove();
    filter_value = element.closest('tr').find('input[id$=filter_value]');
    filter_value2 = element.closest('tr').find('input[id$=filter_value2]');
    switch (selected_type) { 
        case 'isnull':
            if ( filter_value.val() && filter_value.val() != '0'  ) {
                filter_value.after('<input name="check_value" onchange="set_check_value(event)" checked="checked" type="checkbox"/>');
            } else {
                filter_value.after('<input name="check_value" onchange="set_check_value(event)" type="checkbox"/>');
                if ( filter_value.val() == "" ) {
                    filter_value.val('0');
                }
            }
            filter_value.hide();
            filter_value2.hide()
            break;
        case 'range':
            filter_value.show();
            filter_value2.show();
            break;
        default:
            filter_value.show();
            filter_value2.hide();
    }
}

function set_check_value(event) {
    var element = $(event.target);
    var filter_value = element.closest('tr').find('input[id$=filter_value]');
    if(element.is(':checked')) {
        filter_value.val('1');
    } else {
        filter_value.val('0');
    }
}

function refresh_preview() {
    $('#preview_area').html('<div style="height: 16px" id="preview_spinner"></div>');
    $('#preview_spinner').spin('large');
    $.post(  
        path_prefix + "/report_builder/ajax_preview/",  
        {
            csrfmiddlewaretoken: $("input[name=csrfmiddlewaretoken]").val(),
            report_id: $('#report_id').data('id'),
        },
        function(data){
            $('#preview_area').html(data);
        }
    )
    .fail(function(jqXHR, textStatus, errorThrown) {
        var error_message = "<h3>Sorry, there was an error generating your report. Details appear below.</h3>"
        error_message += '<pre>' + jqXHR.responseText + '</pre>';
        $('#preview_area').html(error_message);
    });
}

function aggregate_tip() {
    $('#tip_area').html('Aggregates can have unexpected behavior if used with sort order and the values in your search. To read more check out <a target="_blank" href="https://docs.djangoproject.com/en/dev/topics/db/aggregation/">Django Aggregation</a>')
    $('#tip_area').show('slow');
}

function property_tip() {
    $('#tip_area').html("NOTE: Searching on properties can be <i>very</i> slow.  It's a good idea to add some fields to help speed up your report.")
    $('#tip_area').show('slow');
}

$(function() {
    enable_drag();
    $( "#tabs" ).tabs();
    $("#ui-id-3").click(refresh_preview);
    
    $('#field_list_table').sortable({
        containment: 'parent',
        zindex: 10,
        items: 'tbody tr',
        handle: 'td:first',
        update: function() {
            $(this).find('tbody tr').each(function(i) {
                if ($(this).find('input[id$=name]').val()) {
                    $(this).find('input[id$=position]').val(i+1);
                }
            });
        }
    });
    $('#field_filter_table').sortable({
        containment: 'parent',
        zindex: 10,
        items: 'tbody tr',
        handle: 'td:first',
        update: function() {
            $(this).find('tbody tr').each(function(i) {
                $(this).find('input[id$=position]').val(i+1);
            });
        }
    });
//    $('.filter_table_fields').nestedSortable({
//        toleranceElement: 'parent',
//        items: 'li',
//        handle: 'div'
//        update: function() {
//            $(this).find('tbody tr').each(function(i) {
//                $(this).find('input[id$=position]').val(i+1);
//            });
//        }
//    });
    $('.sortable').nestedSortable({
        handle: 'div',
        items: 'li',
        toleranceElement: '> div'
    });
    $( "#sortable" ).disableSelection();
    // Adjust widgets depending on selected filter type
    $('input[id$=filter_value]').each(function(index, value) {
        element = $(value).closest('tr').find('select[id$=filter_type]');
        check_filter_type(element);
    });
    // Don't forget selects
    $('select[id$=filter_value]').each(function(index, value) {
        element = $(value).closest('tr').find('select[id$=filter_type]');
        check_filter_type(element);
    });
    $( ".datepicker" ).datepicker();
    $('input').change(function() {
        if( $(this).val() != "" )
            window.onbeforeunload = "Are you sure you want to leave?";
    });
    window.onbeforeunload = "Are you sure you want to leave?";
});

function filter(element, list) {
    var value = $(element).val();

    $("#"+list+" li").each(function() {
        if ($(this).text().toUpperCase().search(value.toUpperCase()) > -1) {
            $(this).show();
        }
        else {
            $(this).hide();
        }
    });
}

function toggle_collapse(element) {
    $(element).parent().parent('div.fieldset').children('ul').toggleClass('collapsed');
}

