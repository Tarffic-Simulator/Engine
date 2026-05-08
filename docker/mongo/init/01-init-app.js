const appDatabase = process.env.MONGO_APP_DATABASE;
const appUser = process.env.MONGO_APP_USER;
const appPassword = process.env.MONGO_APP_PASSWORD;

if (!appDatabase || !appUser || !appPassword) {
  throw new Error("Mongo app bootstrap variables are not set.");
}

const appDb = db.getSiblingDB(appDatabase);

if (!appDb.getUser(appUser)) {
  appDb.createUser({
    user: appUser,
    pwd: appPassword,
    roles: [{ role: "readWrite", db: appDatabase }],
  });
}

const collectionNames = ["geographic_areas", "simulations", "simulation_steps"];
const existingCollections = appDb.getCollectionNames();

collectionNames.forEach((collectionName) => {
  if (!existingCollections.includes(collectionName)) {
    appDb.createCollection(collectionName);
  }
});

appDb.geographic_areas.createIndex({ area_id: 1 }, { unique: true, name: "ux_area_id" });
appDb.simulations.createIndex(
  { simulation_id: 1 },
  { unique: true, name: "ux_simulation_id" }
);
appDb.simulation_steps.createIndex(
  { simulation_id: 1, step_number: 1 },
  { unique: true, name: "ux_simulation_step" }
);