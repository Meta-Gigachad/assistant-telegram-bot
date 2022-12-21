CREATE DATABASE nutrition_module;
USE nutrition_module;
CREATE TABLE users ( 
    user_id INT NOT NULL AUTO_INCREMENT, 
    user_name VARCHAR(255), 
    PRIMARY KEY (user_id) 
);
CREATE TABLE food_dictionary ( 
    id INT NOT NULL AUTO_INCREMENT, 
    name VARCHAR(255), 
    calories FLOAT, 
    protein FLOAT, 
    fats FLOAT, 
    carbohydrates FLOAT, 
    added_by_user INT, 
    FOREIGN KEY (added_by_user) REFERENCES users(user_id), 
    PRIMARY KEY (id)
);

CREATE DATABASE training_module;
USE training_module;
CREATE TABLE users ( 
    user_id INT NOT NULL AUTO_INCREMENT, 
    user_name VARCHAR(255), 
    PRIMARY KEY (user_id) 
);

