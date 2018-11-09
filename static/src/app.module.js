angular.module('app',  [
	'ngMaterial', 
	'ngMessages',
	'ngRoute',
	'single-table',
	'two-tables'
]).run(function($log){
	$log.debug("starterApp + ngMaterial running...");
  });