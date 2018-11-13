angular.module('app', [
	'ngMaterial', 
	'ngMessages',
	'ngRoute',
	'single-table',
	'two-tables',
	'metric-table1',
	'metric-table2'
]).run(function($log){
	$log.debug("starterApp + ngMaterial running...");
  });