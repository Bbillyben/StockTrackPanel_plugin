{% load i18n %}

var origgetAvailableTableFilterst = getAvailableTableFilters;
getAvailableTableFilters = function(tableKey) {
     if(tableKey == 'smp_track'){
        return {
            username: {
                title: '{% trans "User Name" %}',
                description: '{% trans "Filter by user name" %}',
            },
            tracktype: {
                title: '{% trans "Operation" %}',
                options: stockHistoryCodes,
            }, 
            lastdate:{
                title: '{% trans "Only Last Date" %}',
                type: 'bool'
            },
            date_greater:{
                title: '{% trans "Date Greater than" %}',
                type: 'date'
            },
            date_lesser:{
                title: '{% trans "Date Lesser than" %}',
                type: 'date'
            },
            batch:{
                title: '{% trans "Batch" %}'
            }, 
            serial:{
                title: '{% trans "Serial" %}'
            },

        };
     }
     
     return origgetAvailableTableFilterst(tableKey);
}


function SMP_initPanel(){
    filterOption={
        download:true,
    }

    var filters = loadTableFilters('smp_track');
    var options={
        queryParams: filters,
        name:'smp_track',        
    }

    setupFilterList('smp_track', $('#SMP_track_table'), '#filter-list-smp_track', filterOption);
    $('#SMP_track_table').inventreeTable(options);
}

$(document).ready(function () {
    SMP_initPanel();
})


