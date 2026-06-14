let x = 10;
x %= 4;
console.log(x);

x **= 3;
console.log(x);

let obj = { count: 5 };
console.log(obj.count++);
console.log(obj.count);
console.log(++obj.count);

let arr = [3];
console.log(arr[0]--);
console.log(arr[0]);
console.log(--arr[0]);

function named() {}
const anonymous = function() {};
const arrow = () => 1;

console.log(named);
console.log(anonymous);
console.log(arrow);
