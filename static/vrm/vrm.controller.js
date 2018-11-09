function vrmController($scope, $http) {
	var ctrl = $scope;
	var myData = [
		{
			firstName: "Cox",
			lastName: "Carney",
			company: "Enormo",
			employed: true
		},
		{
			firstName: "Lorraine",
			lastName: "Wise",
			company: "Comveyer",
			employed: false
		},
		{
			firstName: "Nancy",
			lastName: "Waters",
			company: "Fuelton",
			employed: false
		}
	];
	
	ctrl.gridOptions = {
		enableSorting: true,
		columnDefs: [
		  { field: 'idvrm', width: '10%' },
		  { field: 'name' },
		  { field: 'website' },
		  { field: 'cabins', width: '10%', cellClass: 'text-right' },
		  { field: 'last scrape', type: 'date', cellFilter: 'date:\'yyyy-MM-dd\'' }
		]};
	$http.get('/api/vrm')
		.then(function(response) {
			var ja = []
			for (const data of response.data) {
				ja.push({
					idvrm: data[0],
					name: data[1],
					website: data[2],
					cabins: data[3],
					'last scrape':  data[4]
				})
			}
		ctrl.gridOptions.data = ja;
		}, function(response) {
			var data = response.data || 'Request failed';
			var status = response.status;
			console.log(status, data);
			
		});
	// ctrl.gridOptions.data = myData;

}

angular.
	module("vrm").
	controller("vrmController", vrmController);