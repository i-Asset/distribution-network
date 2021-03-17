package com.github.christophschranz.iot4cpshub;

import com.google.gson.JsonObject;
import org.junit.Test;

import java.util.Properties;

public class Tester {
    /**
     * create required class instances
     */
    public static Properties globalOptions = new Properties();
    public static String expr;
    public static JsonObject jsonInput = new JsonObject();


    @org.junit.Before
    public void setUp() throws Exception {
        globalOptions.setProperty("STREAM_NAME", "test-stream");
        globalOptions.setProperty("SOURCE_SYSTEM", "is.iceland.iot4cps-wp5-WeatherService.Stations");
        globalOptions.setProperty("TARGET_SYSTEM", "cz.icecars.iot4cps-wp5-CarFleet.Car1");
        globalOptions.setProperty("SEMANTIC_SERVER", "127.0.0.1:8082");
        globalOptions.setProperty("FILTER_LOGIC",
                "SELECT * FROM * WHERE (name = 'is.iceland.iot4cps-wp5-WeatherService.Stations.Station_1.Air Temperature' OR name = 'is.iceland.iot4cps-wp5-WeatherService.Stations.Station_2.Air Temperature') AND result < 30;");

        jsonInput.addProperty("quantity", "Air Temperature");
        jsonInput.addProperty("thing", "Station_1");
        jsonInput.addProperty("result", 12.3);
        jsonInput.addProperty("phenomenonTime", "2020-02-24T11:26:02");
        jsonInput.addProperty("time", "2020-02-24T11:26:02");  // adding extra time key
    }

    @Test
    public void test1() {
        System.out.println("#######################################################\n");

        ComparisonNode comNode;
        ArithmeticNode ariNode;

        System.out.println("\n######### Start of recursive tests #############\n");

        expr =  "thing = 'Station_1'";
        try {

            if (!new LogicalNode(expr).evaluate(jsonInput))
                System.out.println("Test 1 failed.");

            expr = "thing = 'Station_1' AND quantity = 'Air Temperature' OR result > 4";
            if (!new LogicalNode(expr).evaluate(jsonInput))
                System.out.println("Test 3 failed.");

            expr = "(quantity = 'Air Temperature' OR result > 4.3210)";
            if (!new LogicalNode(expr).evaluate(jsonInput))
                System.out.println("Test 4 failed.");

            expr = "quantity = 'Air Temperature' OR (result > 30 AND result > 4)";
            if (!new LogicalNode(expr).evaluate(jsonInput))
                System.out.println("Test 4 failed.");

            expr = "((quantity = 'Air Temperature' OR (((result < 30) AND result > 4))))";
            if (!new LogicalNode(expr).evaluate(jsonInput))
                System.out.println("Test 5 failed.");

            expr = "(result < 30 AND result < 4) OR thing = 'Station_1'";
            if (!new LogicalNode(expr).evaluate(jsonInput))
                System.out.println("Test 7 failed.");

            expr = "result < 30 AND result < 4 OR quantity = 'Air Temperature'";  // should be equal than the one above
            if (!new LogicalNode(expr).evaluate(jsonInput))
                System.out.println("Test 8 failed.");
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    @Test
    public void test2() {
        System.out.println("\n######### Start of special operations #############\n");

        try {
            expr =  "result > 0 XOR quantity = 'Air Temperature'";  // intro of XOR
            if (new LogicalNode(expr).evaluate(jsonInput))
                System.out.println("Test 9 failed.");

            expr =  "result = 0 XOR quantity = 'Air Temperature'";  // intro of XOR
            if (!new LogicalNode(expr).evaluate(jsonInput))
                System.out.println("Test 10 failed.");

            expr =  "quantity <> 'Air Temperature'";  // intro of not equal, false
            if (new LogicalNode(expr).evaluate(jsonInput))
                System.out.println("Test 11 failed.");

            expr =  "quantity<>'Air Temperature_123'";  // intro of not equal, true
            LogicalNode logNode = new LogicalNode(expr);
            if (!logNode.evaluate(jsonInput))
                System.out.println("Test 12 failed.");

            expr =  "NOT result> 30";  // intro of not, true
            if (!new LogicalNode(expr).evaluate(jsonInput))
                System.out.println("Test 13 failed.");

            expr =  "thing <> 'Station_123'";  // intro of not equal, true
            if (!new LogicalNode(expr).evaluate(jsonInput))
                System.out.println("Test 14 failed.");

            expr =  " NOT NOT result > 30";  // intro of not, false
            if (new LogicalNode(expr).evaluate(jsonInput))
                System.out.println("Test 15 failed.");

            expr =  "result < 30 AND NOT thing = 'Station_123'";  // intro of not, true
            if (!new LogicalNode(expr).evaluate(jsonInput))
                System.out.println("Test 16 failed.");

            expr =  "NOT (result < 30 AND NOT quantity = 'Air Temperature')";  // intro of not, true
            if (!new LogicalNode(expr).evaluate(jsonInput))
                System.out.println("Test 17 failed.");

            expr =  "NOT NOT (result < 30 AND NOT NOT quantity = 'Air Temperature')";  // intro of not, true
            if (!new LogicalNode(expr).evaluate(jsonInput))
                System.out.println("Test 18 failed.");
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    @Test
    public void test3() {
        System.out.println("\n######### ordering and hierarchy #############\n");
        try {
            // ordering and hierarchy
            expr =  "result < 30 AND result > 4 AND quantity = 'Air Temperature' AND thing = 'Station_1' ";  // true
            if (!new LogicalNode(expr).evaluate(jsonInput))
                System.out.println("Test 20 failed.");

            expr =  "result > 30 AND result > 4 AND quantity = 'Air Temperature' ";  // false
            if (new LogicalNode(expr).evaluate(jsonInput))
                System.out.println("Test 21 failed.");

            expr =  "result < 30 AND result > 4 AND quantity <> 'Air Temperature' ";  // false
            if (new LogicalNode(expr).evaluate(jsonInput))
                System.out.println("Test 23 failed.");

            expr =  "result > 30 AND result > 4 XOR quantity = 'Air Temperature' ";  // true
            if (!new LogicalNode(expr).evaluate(jsonInput))
                System.out.println("Test 24 failed.");

            expr =  "quantity = 'Air Temperature' XOR result > 30 AND result > 4";  // ordering, true
            if (!new LogicalNode(expr).evaluate(jsonInput))
                System.out.println("Test 25 failed.");

            expr =  "result > 30 AND result > 4 OR thing = 'Station_123'";  // false
            if (new LogicalNode(expr).evaluate(jsonInput))
                System.out.println("Test 26 failed.");

            expr =  "thing = 'Station_123' OR result > 30 AND result > 4";  // false
            if (new LogicalNode(expr).evaluate(jsonInput))
                System.out.println("Test 27 failed.");
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    @Test
    public void test4() {
        System.out.println("\n######## Testing arithmetic operations #########\n");
        try {
            expr = "2";
            if (new ArithmeticNode(expr).arithmeticEvaluate() != 2)
                System.out.println("Test 30 failed.");

            expr = "2*3";
            if (new ArithmeticNode(expr).arithmeticEvaluate() != 6)
                System.out.println("Test 31 failed.");

            expr = "2*3-1";
            if (new ArithmeticNode(expr).arithmeticEvaluate() != 5)
                System.out.println("Test 32 failed.");

            expr = "2*3-1*100";
            if (new ArithmeticNode(expr).arithmeticEvaluate() != -94)
                System.out.println("Test 33 failed.");

            expr = "2*(3-1)*100";
            if (new ArithmeticNode(expr).arithmeticEvaluate() != 400)
                System.out.println("Test 34 failed.");

            expr = "2*(3-1)^4";
            if (new ArithmeticNode(expr).arithmeticEvaluate() != 32)
                System.out.println("Test 35 failed.");

            expr = "100 % 13";
            if (new ArithmeticNode(expr).arithmeticEvaluate() != 9)
                System.out.println("Test 36 failed.");

            expr = "((100 ) % 13 ) ";
            if (new ArithmeticNode(expr).arithmeticEvaluate() != 9)
                System.out.println("Test 37 failed.");

            expr = "2*3.1";  // there are rounding errors
            if (Math.abs(new ArithmeticNode(expr).arithmeticEvaluate() - 6.2) > 1E-6)
                System.out.println("Test 38 failed: " + new ArithmeticNode(expr).arithmeticEvaluate());
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    @Test
    public void test5() {
        LogicalNode logNode;
        System.out.println("\n######## Combinations #########\n");
        try {
            expr =  "result < 3*10 AND result > 4-1";
            if (!new LogicalNode(expr).evaluate(jsonInput))
                System.out.println("Test 40 failed.");

            expr =  "result < 100 % 13 AND result > 0.4^10";
            if (new LogicalNode(expr).evaluate(jsonInput))
                System.out.println("Test 41 failed.");

            expr =  "100 > result AND result > 0.4^10";
            if (!new LogicalNode(expr).evaluate(jsonInput))
                System.out.println("Test 42 failed.");

            expr =  "result - 5 < 10";
            if (!new LogicalNode(expr).evaluate(jsonInput))
                System.out.println("Test 43 failed.");

            expr =  "(result - 12.3)^2 = 0";
            if (!new LogicalNode(expr).evaluate(jsonInput))
                System.out.println("Test 44 failed.");

            expr =  "'trickyquantity' = quantity";  // false
            logNode = new LogicalNode(expr);
            if (logNode.evaluate(jsonInput))
                System.out.println("Test 45 failed.");

            expr =  "quantity = 'tricky_result_for this name' XOR result < 30 AND result > 4";
            logNode = new LogicalNode(expr);
            if (!logNode.evaluate(jsonInput))
                System.out.println("Test 46 failed.");

            expr =  "'trickyq<uantity' = quantity";  // false
            logNode = new LogicalNode(expr);
            if (logNode.evaluate(jsonInput))
                System.out.println("Test 47 failed.");

            expr =  "'trickyq<uantity' = quantity";  // false
            logNode = new LogicalNode(expr);
            if (logNode.evaluate(jsonInput))
                System.out.println("Test 48 failed.");

            expr =  "(quantity = 'tricky>AND<for_=_quantity' XOR result < 30) AND result > 4"; // true
            logNode = new LogicalNode(expr);
            if (!logNode.evaluate(jsonInput))
                System.out.println("Test 49 failed.");

        } catch (Exception e) {
            e.printStackTrace();
        }

        System.out.println("\n######## Testing the degree of the trees #########\n");
        try {
            expr = "2*(3-1)*100";
            if (new ArithmeticNode(expr).getDegree() != 3)
                System.out.println("Test 51 failed, -> correct: " + new ArithmeticNode(expr).getDegree());

            expr =  "result < 10^10 % 13 AND result > 0.4^10";
            logNode = new LogicalNode(expr);
            //                System.out.println(logNode.getDegree());
            if (logNode.getDegree() != 4)
                System.out.println("Test 52 failed.");

            expr =  "quantity = 'tricky_result_for this name' XOR result < 30 AND result > 4";
            if (new LogicalNode(expr).getDegree() != 3)
                System.out.println("Test 53 failed, -> correct: " + new LogicalNode(expr).getDegree());
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    @Test
    public void test6() {
        LogicalNode logNode;
        System.out.println("\n######## Testing the degree of the trees #########\n");
        try {
            expr = "2*(3-1)*100";
            if (new ArithmeticNode(expr).getDegree() != 3)
                System.out.println("Test 51 failed, -> correct: " + new ArithmeticNode(expr).getDegree());

            expr =  "result < 10^10 % 13 AND result > 0.4^10";
            logNode = new LogicalNode(expr);
            //                System.out.println(logNode.getDegree());
            if (logNode.getDegree() != 4)
                System.out.println("Test 52 failed.");

            expr =  "quantity = 'tricky_result_for this quantity' XOR result < 30 AND result > 4";
            if (new LogicalNode(expr).getDegree() != 3)
                System.out.println("Test 53 failed, -> correct: " + new LogicalNode(expr).getDegree());
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    @Test
    public void test7() {
        LogicalNode logNode;
        System.out.println("\n######## Testing failures and exits #########\n");
        try {  // should work
            expr =  "quantity = 'tricky_result_for this name' XOR result < 30 AND result > 4";
            new LogicalNode(expr).getDegree();
        } catch (Exception e) {
            e.printStackTrace();
        }
        try {
            expr =  "bad_Quantity = 'wrong keyword'"; // exit code 40
            logNode = new LogicalNode(expr);
        } catch (Exception e) {
            if (!e.toString().startsWith("com.github.christophschranz.iot4cpshub.StreamSQLException: " +
                    "The sanity check fails for expression 'bad_Quantity = 'wrong keyword''."))
                e.printStackTrace();
        }
        try {
            expr =  "TRUE"; // exit code 0
            logNode = new LogicalNode(expr);
            logNode.evaluate(jsonInput);
        } catch (Exception e) {
            e.printStackTrace();
        }
        try {
            expr =  "BAD_TRUE"; // exit code 40
            logNode = new LogicalNode(expr);
            System.out.println(logNode.evaluate(jsonInput));
        } catch (Exception e) {
            if (!e.toString().startsWith("com.github.christophschranz.iot4cpshub.StreamSQLException: " +
                    "The sanity check fails for expression 'BAD_TRUE'."))
                e.printStackTrace();
        }
        try {
            expr =  "quantity = 'tricky_result_for this quantity' XORG result < 30"; // exit code 45
            logNode = new LogicalNode(expr);
            System.out.println(logNode.evaluate(jsonInput));
        } catch (Exception e) {
            if (!e.toString().startsWith("com.github.christophschranz.iot4cpshub.StreamSQLException: " +
                    "The sanity check fails for expression 'quantity = 'tricky_result_for this quantity' XORG result < 30'."))
                e.printStackTrace();
        }
        try {
            expr =  "result ~ 30"; // exit code 41
            logNode = new LogicalNode(expr);
        } catch (Exception e) {
            if (!e.toString().startsWith("com.github.christophschranz.iot4cpshub.StreamSQLException: " +
                    "Couldn't find operator for string expression 'result ~ 30'."))
                e.printStackTrace();
        }
        try {
            expr =  "result = 30'asdf'"; // no exit, but comparison, could also exit in sanity check
            logNode = new LogicalNode(expr);
            logNode.evaluate(jsonInput);
        } catch (Exception e) {
            e.printStackTrace();
        }
        try {
            expr =  "quantity = 'stranger's quantity'";  // exit code 44
            logNode = new LogicalNode(expr);
            System.out.println(logNode.evaluate(jsonInput));
        } catch (Exception e) {
            if (!e.toString().startsWith("com.github.christophschranz.iot4cpshub.StreamSQLException: "))
                e.printStackTrace();
        }
        try {
            expr =  "6 = 'another beer'";  // exit code 40
            logNode = new LogicalNode(expr);
            System.out.println(logNode.evaluate(jsonInput));
        } catch (Exception e) {
            if (!e.toString().startsWith("com.github.christophschranz.iot4cpshub.StreamSQLException"))
                e.printStackTrace();
        }
        try {
            expr =  "result = 30asdf";  // exit code 52
            logNode = new LogicalNode(expr);
            System.out.println(logNode.evaluate(jsonInput));
        } catch (Exception e) {
            if (!e.toString().startsWith("com.github.christophschranz.iot4cpshub.StreamSQLException: "))
                e.printStackTrace();
        }
        try {
            expr =  "result = 10 # pi";  // exit code 52
            logNode = new LogicalNode(expr);
            System.out.println(logNode.evaluate(jsonInput));
        } catch (Exception e) {
            if (!e.toString().startsWith("com.github.christophschranz.iot4cpshub.StreamSQLException:"))
                e.printStackTrace();
        }
        try {
            expr =  "(result < 30)))) AND result > 4)";
            logNode = new LogicalNode(expr);
            System.out.println(logNode);
        } catch (Exception e) {
            if (!e.toString().startsWith("com.github.christophschranz.iot4cpshub.StreamSQLException"))
                e.printStackTrace();
        }
    }

    @Test
    public void test8() {
        System.out.println("\n######## StreamQuery and Semantics class. #########\n");
        StreamQuery streamQuery;
        Semantics semantics;
        JsonObject ds;

        // start test 61
        jsonInput = new JsonObject();
        ds = new JsonObject();
        ds.addProperty("quantity", "temperature");
        ds.addProperty("thing", "Car1");
        jsonInput.add("datastream", ds);
        jsonInput.addProperty("result", 1.23);
        jsonInput.addProperty("phenomenonTime", "2020-02-24T11:26:02");
        jsonInput.addProperty("time", "2020-02-24T11:26:02");  // adding extra time key
        JsonObject attributes = new JsonObject();
        attributes.addProperty("latitude", 47.822495);
        attributes.addProperty("longitude", 13.04113);
        jsonInput.add("attributes", attributes);
//        System.out.println(jsonInput.get("Datastream").getAsJsonObject().get("@iot.id").getAsString());
        globalOptions.setProperty("SOURCE_SYSTEM", "is.iceland.iot4cps-wp5-WeatherService.Stations");
        globalOptions.setProperty("TARGET_SYSTEM", "cz.icecars.iot4cps-wp5-CarFleet.Car1");
        globalOptions.setProperty("KAFKA_BOOTSTRAP_SERVERS", "172.20.38.70:9092,172.20.38.70:9093,172.20.38.70:9094");
        globalOptions.setProperty("SEMANTIC_SERVER", "https://iasset.salzburgresearch.at/registry-service/swagger-ui.html");
        globalOptions.setProperty("FILTER_LOGIC", "SELECT * FROM * WHERE quantity = 'temperature' AND result < 4;");
        try {
            streamQuery = new StreamQuery(globalOptions, true);
            semantics = new Semantics(globalOptions, "AAS", true);
            System.out.println(semantics);
            JsonObject datastreams = new JsonObject();
            JsonObject ds1 = new JsonObject();
            JsonObject ds2 = new JsonObject();

            // This part is only required for SensorThings as it simulates it's datastream structure
            // replace this demo semantic with a structure as {system_name: thing_aas: datastream_name: asdf}
            ds1.addProperty("thing", "Car1");
            ds1.addProperty("quantity", "Air temperature");
            ds2.addProperty("thing", "Car2");
            ds2.addProperty("quantity", "Air temperature");
            datastreams.add("1",ds1);
            datastreams.add("2",ds2);
            semantics.setStreamObjects(datastreams);

            System.out.println("Raw datastreams: " + jsonInput);
            System.out.println("Augmented datastreams: " + semantics.augmentJsonInput(jsonInput));  // should be false
            if (!streamQuery.evaluate(semantics.augmentJsonInput(jsonInput)))
                System.out.println("Test 61 failed.");
        } catch (Exception e) {
            e.printStackTrace();
        }

        // start test 62
        ds.addProperty("quantity", "temperature");
        jsonInput.addProperty("result", 12.34);
        try {
            streamQuery = new StreamQuery(globalOptions, true);
            semantics = new Semantics(globalOptions, "AAS", true);
            if (streamQuery.evaluate(semantics.augmentJsonInput(jsonInput)))
                System.out.println("Test 62 failed.");
        } catch (Exception e) {
            e.printStackTrace();
        }

        // start test 63
        ds.addProperty("quantity", "temperature");
        jsonInput.addProperty("result", 1.23);
        globalOptions.setProperty("FILTER_LOGIC", "SELECT * FROM * WHERE " +
                "(quantity = 'temperature' AND result < 4) OR (quantity = 'acceleration' AND result > 0.8);");
        try {
            streamQuery = new StreamQuery(globalOptions, true);
            semantics = new Semantics(globalOptions, "AAS", true);
            if (!streamQuery.evaluate(semantics.augmentJsonInput(jsonInput)))
                System.out.println("Test 63 failed.");
        } catch (Exception e) {
            e.printStackTrace();
        }

        // start test 64
        ds.addProperty("quantity", "temperature");
        jsonInput.addProperty("result", 12.34);
        globalOptions.setProperty("FILTER_LOGIC", "SELECT * FROM * WHERE " +
                "(quantity = 'temperature' AND result < 4) OR (quantity = 'acceleration' AND result > 0.8);");
        try {
            streamQuery = new StreamQuery(globalOptions, true);
            semantics = new Semantics(globalOptions, "AAS", true);
            if (streamQuery.evaluate(semantics.augmentJsonInput(jsonInput)))
                System.out.println("Test 64 failed.");
        } catch (Exception e) {
            e.printStackTrace();
        }

/*        jsonInput = new JsonObject();
        ds = new JsonObject();
        ds.addProperty("@iot.id", "2");
        jsonInput.add("Datastream", ds);
        jsonInput.addProperty("result", -5);
        jsonInput.addProperty("phenomenonTime", "2020-02-24T11:26:02");
        jsonInput.addProperty("time", "2020-02-24T11:26:02");  // adding extra time key
//                System.out.println(jsonInput.get("Datastream").getAsJsonObject().get("@iot.id").getAsString());

        globalOptions.setProperty("SOURCE_SYSTEM", "is.iceland.iot4cps-wp5-WeatherService.Stations");
        globalOptions.setProperty("TARGET_SYSTEM", "cz.icecars.iot4cps-wp5-CarFleet.Car1");
        globalOptions.setProperty("FILTER_LOGIC", "SELECT * FROM * WHERE " +
                "(name = 'cz.icecars.iot4cps-wp5-CarFleet.Car1.Main.Air Temperature' OR " +
                "name = 'cz.icecars.iot4cps-wp5-CarFleet.Car2.Main.Air Temperature') AND result < -3.99;");
        try {
            streamQuery = new StreamQuery(globalOptions);
            semantics = new Semantics(globalOptions, "SensorThings");
            JsonObject datastreams = new JsonObject();
            JsonObject ds1 = new JsonObject();
            JsonObject ds2 = new JsonObject();

            ds1.addProperty("@iot.id", 1);
            ds1.addProperty("name", "cz.icecars.iot4cps-wp5-CarFleet.Car1");
            ds2.addProperty("@iot.id", 2);
            ds2.addProperty("name", "cz.icecars.iot4cps-wp5-CarFleet.Car2");
            datastreams.add("1",ds1);
            datastreams.add("2",ds2);
            semantics.setSensorThingsStreams(datastreams);

            JsonObject augmentedJson = semantics.augmentJsonInput(jsonInput);
            assertNotNull("Test 62 failed.", augmentedJson.get("name"));
            assertTrue("Test 63 failed.", streamQuery.evaluate(semantics.augmentJsonInput(jsonInput)));

        } catch (Exception e) {
            e.printStackTrace();
        }*/

//                globalOptions.setProperty("FILTER_LOGIC", "SELECT * FROM is.iceland.iot4cps-wp5-WeatherService.Stations AS s" +
//                        "WHERE (s.name = 'Station_1.Air Temperature' OR s.name = 'Station_2.Air Temperature') AND result < 30;");
//                globalOptions.setProperty("FILTER_LOGIC", "SELECT * FROM is.iceland.iot4cps-wp5-WeatherService.Stations AS st,is.iceland.iot4cps-wp5-WeatherService.Services AS se" +
//                        "WHERE (st.name = 'Station_1.Air Temperature' OR se.name = 'Service_3.temp_in_1_hour') AND result < 30;");
        /* how to query here? What is the instance, and what the table??
         */
//                try {
//                        streamQuery = new StreamQuery(globalOptions);
//                        System.out.println(streamQuery);
//                        System.out.println(streamQuery.conditionTree.child1);
//                        System.out.println(streamQuery.conditionTree.child1.child1.child1);
//                        System.out.println(streamQuery.evaluate(jsonInput));
//                } catch (StreamSQLException e) {
//                        e.printStackTrace();
//                }

    }
}