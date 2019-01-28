function processOrders(orders) {
    var shelves = {
        "cold": "#coldOrderDataTable",
        "hot": "#hotOrderDataTable",
        "frozen": "#frozenOrderDataTable",
        "overflow": "#overflowOrderDataTable"
    }

    for (var temp in shelves) {

        var tableId = shelves[temp]

        $(tableId).find("tr:gt(0)").remove();


        console.log(orders)
        console.log("*")

        function drawTable(data, tableId) {
            for (var i = 0; i < data.length; i++) {
                drawRow(i, data[i], tableId);
            }
        }

        function drawRow(number, rowData, tableId) {
            var row = $("<tr class='trow' />");
            $(tableId).append(row);
            row.append($("<td class='ctd'>" + (number + 1) + "</td>"));
            row.append($("<td class='ctd'>" + rowData.id + "</td>"));
            row.append($("<td class='ctd'>" + rowData.name + "</td>"));
            row.append($("<td class='ctd'>" + rowData.expirationAge + "</td>"));
            row.append($("<td class='ctd'>" + rowData.currentAge + "</td>"));
            row.append($("<td class='ctd'>" + rowData.normalizedValue + "</td>"));
            row.append($("<td class='ctd'>" + rowData.temp + "</td>"));
            row.append($("<td class='ctd'>" + rowData.shelfLife + "</td>"));
            row.append($("<td class='ctd'>" + rowData.decayRate + "</td>"));
        }

        drawTable(orders[temp], tableId);
    }
}