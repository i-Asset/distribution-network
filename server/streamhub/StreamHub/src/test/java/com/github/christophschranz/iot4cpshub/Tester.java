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
        globalOptions.setProperty("SOURCE_SYSTEM", "at.srfg.WeatherService.Stations");
        globalOptions.setProperty("TARGET_SYSTEM", "at.srfg.MachineFleet.Machine1");
/*        globalOptions.setProperty("SERVER_URI", "127.0.0.1:8082");*/
        globalOptions.setProperty("FILTER_LOGIC",
                "SELECT * FROM * WHERE (name = 'at.srfg.WeatherService.Stations.Station_1.temperature' OR name = 'at.srfg.WeatherService.Stations.Station_2.temperature') AND result < 30;");

        // Build a flattened! demo datastream
        JsonObject jsonDSInput = new JsonObject();
        jsonInput.addProperty("quantity", "temperature");
        jsonInput.addProperty("thing", "Station_1");
        jsonInput.addProperty("client_app", "weatherstation_1");
        jsonInput.addProperty("result", 12.3);
        jsonInput.addProperty("phenomenonTime", "2021-06-28T06:35:01.416978+00:00");
        jsonInput.addProperty("resultTime", "2021-06-28T06:35:01.417075+00:00");  // adding extra time key
        System.out.println("Demo data event:\n" + jsonInput);
    /*
        // Flatten the input
        JsonObject flatJsonInput = new JsonObject();
        flatJsonInput.addProperty("quantity", jsonInput.get("datastream").getAsJsonObject().get("quantity").getAsString());
        flatJsonInput.addProperty("thing", jsonInput.get("datastream").getAsJsonObject().get("thing").getAsString());
        flatJsonInput.addProperty("client_app", jsonInput.get("datastream").getAsJsonObject().get("client_app").getAsString());
        flatJsonInput.addProperty("phenomenonTime", jsonInput.get("phenomenonTime").getAsString());
        flatJsonInput.addProperty("resultTime", jsonInput.get("resultTime").getAsString());
        flatJsonInput.addProperty("result", jsonInput.get("result").getAsDouble());*/

    }

    @Test
    public void test1() {
        System.out.println("#######################################################\n");
        System.out.println("\n######### Start of recursive tests #############\n");

        expr =  "thing = 'Station_1'";
        try {

            if (!new LogicalNode(expr).evaluate(jsonInput))
                System.out.println("Test 1 failed.");

            expr = "thing = 'Station_1' AND quantity = 'temperature' OR result > 4";
            if (!new LogicalNode(expr).evaluate(jsonInput))
                System.out.println("Test 3 failed.");

            expr = "(quantity = 'temperature' OR result > 4.3210)";
            if (!new LogicalNode(expr).evaluate(jsonInput))
                System.out.println("Test 4 failed.");

            expr = "quantity = 'temperature' OR (result > 30 AND result > 4)";
            if (!new LogicalNode(expr).evaluate(jsonInput))
                System.out.println("Test 4 failed.");

            expr = "((quantity = 'temperature' OR (((result < 30) AND result > 4))))";
            if (!new LogicalNode(expr).evaluate(jsonInput))
                System.out.println("Test 5 failed.");

            expr = "(result < 30 AND result < 4) OR thing = 'Station_1'";
            if (!new LogicalNode(expr).evaluate(jsonInput))
                System.out.println("Test 7 failed.");

            expr = "result < 30 AND result < 4 OR quantity = 'temperature'";  // should be equal than the one above
            if (!new LogicalNode(expr).evaluate(jsonInput))
                System.out.println("Test 8 failed.");

            expr = "result < 30 AND client_app = 'weatherstation_1'";
            if (!new LogicalNode(expr).evaluate(jsonInput))
                System.out.println("Test 8.2 failed.");
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    @Test
    public void test2() {
        System.out.println("\n######### Start of special operations #############\n");

        try {
            expr =  "result > 0 XOR quantity = 'temperature'";  // intro of XOR
            if (new LogicalNode(expr).evaluate(jsonInput))
                System.out.println("Test 9 failed.");

            expr =  "result = 0 XOR quantity = 'temperature'";  // intro of XOR
            if (!new LogicalNode(expr).evaluate(jsonInput))
                System.out.println("Test 10 failed.");

            expr =  "quantity <> 'temperature'";  // intro of not equal, false
            if (new LogicalNode(expr).evaluate(jsonInput))
                System.out.println("Test 11 failed.");

            expr =  "quantity<>'temperature_123'";  // intro of not equal, true
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

            expr =  "NOT (result < 30 AND NOT quantity = 'temperature')";  // intro of not, true
            if (!new LogicalNode(expr).evaluate(jsonInput))
                System.out.println("Test 17 failed.");

            expr =  "NOT NOT (result < 30 AND NOT NOT quantity = 'temperature')";  // intro of not, true
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
            expr =  "result < 30 AND result > 4 AND quantity = 'temperature' AND thing = 'Station_1' ";  // true
            if (!new LogicalNode(expr).evaluate(jsonInput))
                System.out.println("Test 20 failed.");

            expr =  "result > 30 AND result > 4 AND quantity = 'temperature' ";  // false
            if (new LogicalNode(expr).evaluate(jsonInput))
                System.out.println("Test 21 failed.");

            expr =  "result < 30 AND result > 4 AND quantity <> 'temperature' ";  // false
            if (new LogicalNode(expr).evaluate(jsonInput))
                System.out.println("Test 23 failed.");

            expr =  "result > 30 AND result > 4 XOR quantity = 'temperature' ";  // true
            if (!new LogicalNode(expr).evaluate(jsonInput))
                System.out.println("Test 24 failed.");

            expr =  "quantity = 'temperature' XOR result > 30 AND result > 4";  // ordering, true
            if (!new LogicalNode(expr).evaluate(jsonInput))
                System.out.println("Test 25 failed.");

            expr =  "result > 30 AND result > 4 OR client_app = 'weatherstation_123'";  // false
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

            expr = "2*3.1";  // there is a rounding issue
            if (Math.abs(new ArithmeticNode(expr).arithmeticEvaluate() - 6.2) > 1E-6)
                System.out.println("Test 38 failed: " + new ArithmeticNode(expr).arithmeticEvaluate());

            expr = "10+1+5-2-2+5-3*3.1";  // there are rounding errors
            if (Math.abs(new ArithmeticNode(expr).arithmeticEvaluate() - 7.7) > 1E-6)
                System.out.println("Test 39 failed: " + expr + " gets evaluated as " + new ArithmeticNode(expr).arithmeticEvaluate());
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

            expr =  "quantity = 'tricky_result-for this name' XOR result < 30 AND result > 4";
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
        ds.addProperty("client_app", "control");
        jsonInput.add("datastream", ds);
        jsonInput.addProperty("result", 1.23);
        jsonInput.addProperty("phenomenonTime", "2020-02-24T11:26:02");
        jsonInput.addProperty("time", "2020-02-24T11:26:02");  // adding extra time key
        JsonObject attributes = new JsonObject();
        attributes.addProperty("latitude", 47.822495);
        attributes.addProperty("longitude", 13.04113);
        jsonInput.add("attributes", attributes);
//        System.out.println(jsonInput.get("Datastream").getAsJsonObject().get("@iot.id").getAsString());
        globalOptions.setProperty("SOURCE_SYSTEM", "at.srfg.WeatherService.Stations");
        globalOptions.setProperty("TARGET_SYSTEM", "at.srfg.MachineFleet.Machine1");
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
            ds1.addProperty("thing", "Machine1");
            ds1.addProperty("quantity", "temperature");
            ds2.addProperty("thing", "Machine2");
            ds2.addProperty("quantity", "temperature");
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

        globalOptions.setProperty("SOURCE_SYSTEM", "at.srfg.WeatherService.Stations");
        globalOptions.setProperty("TARGET_SYSTEM", "at.srfg.MachineFleet.Machine1");
        globalOptions.setProperty("FILTER_LOGIC", "SELECT * FROM * WHERE " +
                "(name = 'at.srfg.MachineFleet.Machine1.temperature' OR " +
                "name = 'at.srfg.MachineFleet.Machine2.temperature') AND result < -3.99;");
        try {
            streamQuery = new StreamQuery(globalOptions);
            semantics = new Semantics(globalOptions, "SensorThings");
            JsonObject datastreams = new JsonObject();
            JsonObject ds1 = new JsonObject();
            JsonObject ds2 = new JsonObject();

            ds1.addProperty("@iot.id", 1);
            ds1.addProperty("name", "at.srfg.MachineFleet.Machine1");
            ds2.addProperty("@iot.id", 2);
            ds2.addProperty("name", "at.srfg.MachineFleet.Machine2");
            datastreams.add("1",ds1);
            datastreams.add("2",ds2);
            semantics.setSensorThingsStreams(datastreams);

            JsonObject augmentedJson = semantics.augmentJsonInput(jsonInput);
            assertNotNull("Test 62 failed.", augmentedJson.get("name"));
            assertTrue("Test 63 failed.", streamQuery.evaluate(semantics.augmentJsonInput(jsonInput)));

        } catch (Exception e) {
            e.printStackTrace();
        }*/

//                globalOptions.setProperty("FILTER_LOGIC", "SELECT * FROM at.srfg.WeatherService.Stations AS s" +
//                        "WHERE (s.name = 'Station_1.temperature' OR s.name = 'Station_2.temperature') AND result < 30;");
//                globalOptions.setProperty("FILTER_LOGIC", "SELECT * FROM at.srfg.WeatherService.Stations AS st, at.srfg.MachineFleet.Machine1 AS m1" +
//                        "WHERE (st.name = 'Station_1.temperature' OR se.name = 'Service_3.temp_in_1_hour') AND result < 30;");
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