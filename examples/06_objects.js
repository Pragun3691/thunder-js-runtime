const user = {
    name: "Pragun",
    age: 20
};

console.log(user.name);
console.log(user["age"]);

user.age = 21;
user.city = "Patiala";

console.log(user.age);
console.log(user.city);
console.log(user.missing);
