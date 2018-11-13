angular.module('app')
	.config(['$locationProvider', '$routeProvider', '$mdThemingProvider',
		function config($locationProvider, $routeProvider, $mdThemingProvider) {
		$locationProvider.hashPrefix('!');
		$mdThemingProvider.theme('default').primaryPalette('blue-grey');

		$routeProvider.
			when('/', {
				controller: "singleTableController",
				templateUrl: "src/single-table/single-table.template.html"
			}).
			when('/metrics', {
				template: "<metric-table1></metric-table1><metric-table2></metric-table2>"
			}).
			when('/:view', {
				controller: "singleTableController",
				templateUrl: "src/single-table/single-table.template.html"
			}).
			when('/report/1', {
				controller: "twoTablesController",
				templateUrl: "src/two-tables/two-tables.template.html"
			}).
			otherwise({
				templateUrl: "404.html"
			});
		}
	]);