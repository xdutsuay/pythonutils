// This is a single-line comment
/*
   This is a multi-line comment
*/

// Variables and Data Types
var greeting = "Hello, World!"; // String
var number = 42; // Number
var isTrue = true; // Boolean

// Arrays
var fruits = ["apple", "banana", "cherry"];

// Objects
var person = {
  firstName: "John",
  lastName: "Doe",
  age: 30
};

// Conditional Statements
if (number > 10) {
  console.log("Number is greater than 10");
} else {
  console.log("Number is not greater than 10");
}

// Loops
for (var i = 0; i < fruits.length; i++) {
  console.log(fruits[i]);
}

// Functions
function sayHello(name) {
  console.log("Hello, " + name);
}

sayHello("Alice");

// Events
document.getElementById("myButton").addEventListener("click", function() {
  console.log("Button clicked!");
});

// DOM Manipulation
var element = document.getElementById("myElement");
element.innerHTML = "New content";

// Try-Catch for Error Handling
try {
  var result = undefinedVariable + 10;
} catch (error) {
  console.error("An error occurred: " + error);
}

// While Loop
var count = 0;
while (count < 5) {
  console.log("Count: " + count);
  count++;
}

// Switch Statement
var day = "Monday";
switch (day) {
  case "Monday":
    console.log("It's the start of the week.");
    break;
  case "Friday":
    console.log("Weekend is coming!");
    break;
  default:
    console.log("It's a regular day.");
}

// Arrays: Adding and Removing Elements
fruits.push("grape");
fruits.pop();

// Operators
var x = 5;
var y = 3;
var sum = x + y;
var difference = x - y;
var product = x * y;
var quotient = x / y;
var remainder = x % y;

// Alerts
alert("This is an alert!");

// Comments
// Comments are ignored by the JavaScript interpreter.

// End of the JavaScript program
