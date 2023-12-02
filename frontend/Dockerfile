FROM node:18-slim

WORKDIR /app

# add `/app/node_modules/.bin` to $PATH
ENV PATH /app/node_modules/.bin:$PATH

# install app dependencies
# copy to root of the working directory
COPY package.json .
# COPY yarn.lock /app
RUN yarn install
# RUN npm install react-scripts@3.4.1 -g --silent

# add app
COPY . .

EXPOSE 3000

CMD ["yarn", "start"]




