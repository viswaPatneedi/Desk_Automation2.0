--
-- PostgreSQL database dump
--

\restrict Kr6bX7S9a6DWEOfw5QYf4Wty2LXMruREvvT9jJKnASsyBYtX1fsS8P917QDi7G3

-- Dumped from database version 16.14 (Debian 16.14-1.pgdg13+1)
-- Dumped by pg_dump version 16.14 (Debian 16.14-1.pgdg13+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Data for Name: agent_status; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agent_status (id, agent_name, is_running, last_heartbeat, task_count_total, task_count_completed, task_count_failed, error_message, health_status, metrics, updated_at) FROM stdin;
\.


--
-- Data for Name: app_credentials; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.app_credentials (id, credential_id, app_name, username, password, login_url, profile_name, api_key, custom_config, app_version, device_type, is_primary, team_name, location, created_by, created_at, updated_at, updated_by, is_active, last_used_at, usage_count) FROM stdin;
1	netflix_LRQA_5d56e28d	netflix	tester_nbr1@netflix.com	1717@Arch	https://www.netflix.com/tv2		\N	\N	\N		t	LRQA	\N	\N	2026-08-03 13:38:28.944468	2026-08-03 13:38:28.944497	\N	t	\N	0
2	disney_plus_LRQA_cbdf808a	disney_plus	rdkmwlrqteam@comcast.com	Qwerty12345+	https://www.disneyplus.com/identity/begin?cid=DSS-OFFDEVICE-LP		\N	\N	\N		t	LRQA	\N	\N	2026-08-03 13:38:28.944468	2026-08-03 13:45:26.058419	\N	t	\N	0
3	youtube_LRQA_8004134e	youtube	cperdkemiddleware@gmail.com	Qwerty#6680	https://yt.be/activate		\N	\N	\N		t	LRQA	\N	\N	2026-08-03 13:38:28.944468	2026-08-03 13:38:28.944497	\N	t	\N	0
4	youtube_LRQA_97aad10c	youtube	cperdkemiddleware@gmail.com	Qwerty#6680	yt.be/activate		\N	\N	\N		f	LRQA	\N	\N	2026-08-03 13:38:28.944468	2026-08-03 13:38:28.944497	\N	t	\N	0
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.users (id, username, password_hash, email, team_name, is_admin, is_approved, created_at, updated_at, last_login, active) FROM stdin;
\.


--
-- Data for Name: audit_logs; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.audit_logs (id, action_type, entity_type, entity_id, performed_by, old_values, new_values, reason, impact_assessment, status, "timestamp", is_immutable) FROM stdin;
1	db_rollback	database_transaction	job#fc6fa935-cfc8-4cd2-93cc-22b9f4567896	\N	\N	{"error": "(psycopg2.errors.UndefinedColumn) column \\"session_folder\\" of relation \\"jobs\\" does not exist\\nLINE 1: ...ion_results, start_time, end_time, log_file_path, session_fo...\\n                                                             ^\\n\\n[SQL: INSERT INTO jobs (job_id, user_id, device_id, device_ip, device_name, execution_queue, methods, iterations, sequence_id, sequence_name, execution_type, status, execution_context_id, current_step, current_iteration, iteration_results, start_time, end_time, log_file_path, session_folder, team_name, created_at, updated_at) VALUES (%(job_id)s, %(user_id)s, %(device_id)s, %(device_ip)s, %(device_name)s, %(execution_queue)s, %(methods)s, %(iterations)s, %(sequence_id)s, %(sequence_name)s, %(execution_type)s, %(status)s, %(execution_context_id)s, %(current_step)s, %(current_iteration)s, %(iteration_results)s, %(start_time)s, %(end_time)s, %(log_file_path)s, %(session_folder)s, %(team_name)s, %(created_at)s, %(updated_at)s) RETURNING jobs.id]\\n[parameters: {'job_id': 'fc6fa935-cfc8-4cd2-93cc-22b9f4567896', 'user_id': 'vpatne290', 'device_id': None, 'device_ip': '10.0.0.250', 'device_name': 'ELEMENT_A4K', 'execution_queue': '[{\\"method\\": \\"ir_test\\", \\"ir_keys\\": [\\"HOME\\"], \\"ir_key_delay\\": 0.5, \\"description\\": \\"Switching the device ON\\"}]', 'methods': '[\\"ir_test\\"]', 'iterations': 1, 'sequence_id': None, 'sequence_name': None, 'execution_type': 'direct_method', 'status': 'pending', 'execution_context_id': None, 'current_step': 0, 'current_iteration': 0, 'iteration_results': '{}', 'start_time': None, 'end_time': None, 'log_file_path': None, 'session_folder': None, 'team_name': 'LRQA', 'created_at': datetime.datetime(2026, 8, 3, 20, 13, 12, 650136, tzinfo=datetime.timezone.utc), 'updated_at': datetime.datetime(2026, 8, 3, 20, 13, 12, 650138, tzinfo=datetime.timezone.utc)}]\\n(Background on this error at: https://sqlalche.me/e/20/f405)", "operation": "create_job", "transaction_id": "job#fc6fa935-cfc8-4cd2-93cc-22b9f4567896"}	\N	\N	success	2026-08-03 16:13:12.654255	t
2	db_rollback	database_transaction	job#fc6fa935-cfc8-4cd2-93cc-22b9f4567896	\N	\N	{"error": "(psycopg2.errors.UndefinedColumn) column jobs.session_folder does not exist\\nLINE 1: ...d_time, jobs.log_file_path AS jobs_log_file_path, jobs.sessi...\\n                                                             ^\\n\\n[SQL: SELECT jobs.id AS jobs_id, jobs.job_id AS jobs_job_id, jobs.user_id AS jobs_user_id, jobs.device_id AS jobs_device_id, jobs.device_ip AS jobs_device_ip, jobs.device_name AS jobs_device_name, jobs.execution_queue AS jobs_execution_queue, jobs.methods AS jobs_methods, jobs.iterations AS jobs_iterations, jobs.sequence_id AS jobs_sequence_id, jobs.sequence_name AS jobs_sequence_name, jobs.execution_type AS jobs_execution_type, jobs.status AS jobs_status, jobs.execution_context_id AS jobs_execution_context_id, jobs.current_step AS jobs_current_step, jobs.current_iteration AS jobs_current_iteration, jobs.iteration_results AS jobs_iteration_results, jobs.start_time AS jobs_start_time, jobs.end_time AS jobs_end_time, jobs.log_file_path AS jobs_log_file_path, jobs.session_folder AS jobs_session_folder, jobs.team_name AS jobs_team_name, jobs.created_at AS jobs_created_at, jobs.updated_at AS jobs_updated_at \\nFROM jobs \\nWHERE jobs.job_id = %(job_id_1)s \\n LIMIT %(param_1)s]\\n[parameters: {'job_id_1': 'fc6fa935-cfc8-4cd2-93cc-22b9f4567896', 'param_1': 1}]\\n(Background on this error at: https://sqlalche.me/e/20/f405)", "operation": "update_job_status", "transaction_id": "job#fc6fa935-cfc8-4cd2-93cc-22b9f4567896"}	\N	\N	success	2026-08-03 16:13:12.74017	t
3	db_rollback	database_transaction	job#fc6fa935-cfc8-4cd2-93cc-22b9f4567896	\N	\N	{"error": "(psycopg2.errors.UndefinedColumn) column jobs.session_folder does not exist\\nLINE 1: ...d_time, jobs.log_file_path AS jobs_log_file_path, jobs.sessi...\\n                                                             ^\\n\\n[SQL: SELECT jobs.id AS jobs_id, jobs.job_id AS jobs_job_id, jobs.user_id AS jobs_user_id, jobs.device_id AS jobs_device_id, jobs.device_ip AS jobs_device_ip, jobs.device_name AS jobs_device_name, jobs.execution_queue AS jobs_execution_queue, jobs.methods AS jobs_methods, jobs.iterations AS jobs_iterations, jobs.sequence_id AS jobs_sequence_id, jobs.sequence_name AS jobs_sequence_name, jobs.execution_type AS jobs_execution_type, jobs.status AS jobs_status, jobs.execution_context_id AS jobs_execution_context_id, jobs.current_step AS jobs_current_step, jobs.current_iteration AS jobs_current_iteration, jobs.iteration_results AS jobs_iteration_results, jobs.start_time AS jobs_start_time, jobs.end_time AS jobs_end_time, jobs.log_file_path AS jobs_log_file_path, jobs.session_folder AS jobs_session_folder, jobs.team_name AS jobs_team_name, jobs.created_at AS jobs_created_at, jobs.updated_at AS jobs_updated_at \\nFROM jobs \\nWHERE jobs.job_id = %(job_id_1)s \\n LIMIT %(param_1)s]\\n[parameters: {'job_id_1': 'fc6fa935-cfc8-4cd2-93cc-22b9f4567896', 'param_1': 1}]\\n(Background on this error at: https://sqlalche.me/e/20/f405)", "operation": "update_iteration_result", "transaction_id": "job#fc6fa935-cfc8-4cd2-93cc-22b9f4567896"}	\N	\N	success	2026-08-03 16:13:29.66502	t
4	db_rollback	database_transaction	job#fc6fa935-cfc8-4cd2-93cc-22b9f4567896	\N	\N	{"error": "(psycopg2.errors.UndefinedColumn) column jobs.session_folder does not exist\\nLINE 1: ...d_time, jobs.log_file_path AS jobs_log_file_path, jobs.sessi...\\n                                                             ^\\n\\n[SQL: SELECT jobs.id AS jobs_id, jobs.job_id AS jobs_job_id, jobs.user_id AS jobs_user_id, jobs.device_id AS jobs_device_id, jobs.device_ip AS jobs_device_ip, jobs.device_name AS jobs_device_name, jobs.execution_queue AS jobs_execution_queue, jobs.methods AS jobs_methods, jobs.iterations AS jobs_iterations, jobs.sequence_id AS jobs_sequence_id, jobs.sequence_name AS jobs_sequence_name, jobs.execution_type AS jobs_execution_type, jobs.status AS jobs_status, jobs.execution_context_id AS jobs_execution_context_id, jobs.current_step AS jobs_current_step, jobs.current_iteration AS jobs_current_iteration, jobs.iteration_results AS jobs_iteration_results, jobs.start_time AS jobs_start_time, jobs.end_time AS jobs_end_time, jobs.log_file_path AS jobs_log_file_path, jobs.session_folder AS jobs_session_folder, jobs.team_name AS jobs_team_name, jobs.created_at AS jobs_created_at, jobs.updated_at AS jobs_updated_at \\nFROM jobs \\nWHERE jobs.job_id = %(job_id_1)s \\n LIMIT %(param_1)s]\\n[parameters: {'job_id_1': 'fc6fa935-cfc8-4cd2-93cc-22b9f4567896', 'param_1': 1}]\\n(Background on this error at: https://sqlalche.me/e/20/f405)", "operation": "update_job_status", "transaction_id": "job#fc6fa935-cfc8-4cd2-93cc-22b9f4567896"}	\N	\N	success	2026-08-03 16:13:30.384887	t
5	db_rollback	database_transaction	job#a3fdea26-8d57-40bd-95cb-3b2b229b9f93	\N	\N	{"error": "(psycopg2.errors.UndefinedColumn) column \\"session_folder\\" of relation \\"jobs\\" does not exist\\nLINE 1: ...ion_results, start_time, end_time, log_file_path, session_fo...\\n                                                             ^\\n\\n[SQL: INSERT INTO jobs (job_id, user_id, device_id, device_ip, device_name, execution_queue, methods, iterations, sequence_id, sequence_name, execution_type, status, execution_context_id, current_step, current_iteration, iteration_results, start_time, end_time, log_file_path, session_folder, team_name, created_at, updated_at) VALUES (%(job_id)s, %(user_id)s, %(device_id)s, %(device_ip)s, %(device_name)s, %(execution_queue)s, %(methods)s, %(iterations)s, %(sequence_id)s, %(sequence_name)s, %(execution_type)s, %(status)s, %(execution_context_id)s, %(current_step)s, %(current_iteration)s, %(iteration_results)s, %(start_time)s, %(end_time)s, %(log_file_path)s, %(session_folder)s, %(team_name)s, %(created_at)s, %(updated_at)s) RETURNING jobs.id]\\n[parameters: {'job_id': 'a3fdea26-8d57-40bd-95cb-3b2b229b9f93', 'user_id': 'vpatne290', 'device_id': None, 'device_ip': '10.0.0.250', 'device_name': 'ELEMENT_A4K', 'execution_queue': '[{\\"method\\": \\"ir_test\\", \\"ir_keys\\": [\\"HOME\\"], \\"ir_key_delay\\": 0.5}]', 'methods': '[\\"ir_test\\"]', 'iterations': 1, 'sequence_id': None, 'sequence_name': None, 'execution_type': 'direct_method', 'status': 'pending', 'execution_context_id': None, 'current_step': 0, 'current_iteration': 0, 'iteration_results': '{}', 'start_time': None, 'end_time': None, 'log_file_path': None, 'session_folder': None, 'team_name': 'LRQA', 'created_at': datetime.datetime(2026, 8, 5, 0, 25, 25, 368341, tzinfo=datetime.timezone.utc), 'updated_at': datetime.datetime(2026, 8, 5, 0, 25, 25, 368342, tzinfo=datetime.timezone.utc)}]\\n(Background on this error at: https://sqlalche.me/e/20/f405)", "operation": "create_job", "transaction_id": "job#a3fdea26-8d57-40bd-95cb-3b2b229b9f93"}	\N	\N	success	2026-08-04 20:25:25.372343	t
6	db_rollback	database_transaction	job#a3fdea26-8d57-40bd-95cb-3b2b229b9f93	\N	\N	{"error": "(psycopg2.errors.UndefinedColumn) column jobs.session_folder does not exist\\nLINE 1: ...d_time, jobs.log_file_path AS jobs_log_file_path, jobs.sessi...\\n                                                             ^\\n\\n[SQL: SELECT jobs.id AS jobs_id, jobs.job_id AS jobs_job_id, jobs.user_id AS jobs_user_id, jobs.device_id AS jobs_device_id, jobs.device_ip AS jobs_device_ip, jobs.device_name AS jobs_device_name, jobs.execution_queue AS jobs_execution_queue, jobs.methods AS jobs_methods, jobs.iterations AS jobs_iterations, jobs.sequence_id AS jobs_sequence_id, jobs.sequence_name AS jobs_sequence_name, jobs.execution_type AS jobs_execution_type, jobs.status AS jobs_status, jobs.execution_context_id AS jobs_execution_context_id, jobs.current_step AS jobs_current_step, jobs.current_iteration AS jobs_current_iteration, jobs.iteration_results AS jobs_iteration_results, jobs.start_time AS jobs_start_time, jobs.end_time AS jobs_end_time, jobs.log_file_path AS jobs_log_file_path, jobs.session_folder AS jobs_session_folder, jobs.team_name AS jobs_team_name, jobs.created_at AS jobs_created_at, jobs.updated_at AS jobs_updated_at \\nFROM jobs \\nWHERE jobs.job_id = %(job_id_1)s \\n LIMIT %(param_1)s]\\n[parameters: {'job_id_1': 'a3fdea26-8d57-40bd-95cb-3b2b229b9f93', 'param_1': 1}]\\n(Background on this error at: https://sqlalche.me/e/20/f405)", "operation": "update_job_status", "transaction_id": "job#a3fdea26-8d57-40bd-95cb-3b2b229b9f93"}	\N	\N	success	2026-08-04 20:25:25.453951	t
7	db_rollback	database_transaction	job#a3fdea26-8d57-40bd-95cb-3b2b229b9f93	\N	\N	{"error": "(psycopg2.errors.UndefinedColumn) column jobs.session_folder does not exist\\nLINE 1: ...d_time, jobs.log_file_path AS jobs_log_file_path, jobs.sessi...\\n                                                             ^\\n\\n[SQL: SELECT jobs.id AS jobs_id, jobs.job_id AS jobs_job_id, jobs.user_id AS jobs_user_id, jobs.device_id AS jobs_device_id, jobs.device_ip AS jobs_device_ip, jobs.device_name AS jobs_device_name, jobs.execution_queue AS jobs_execution_queue, jobs.methods AS jobs_methods, jobs.iterations AS jobs_iterations, jobs.sequence_id AS jobs_sequence_id, jobs.sequence_name AS jobs_sequence_name, jobs.execution_type AS jobs_execution_type, jobs.status AS jobs_status, jobs.execution_context_id AS jobs_execution_context_id, jobs.current_step AS jobs_current_step, jobs.current_iteration AS jobs_current_iteration, jobs.iteration_results AS jobs_iteration_results, jobs.start_time AS jobs_start_time, jobs.end_time AS jobs_end_time, jobs.log_file_path AS jobs_log_file_path, jobs.session_folder AS jobs_session_folder, jobs.team_name AS jobs_team_name, jobs.created_at AS jobs_created_at, jobs.updated_at AS jobs_updated_at \\nFROM jobs \\nWHERE jobs.job_id = %(job_id_1)s \\n LIMIT %(param_1)s]\\n[parameters: {'job_id_1': 'a3fdea26-8d57-40bd-95cb-3b2b229b9f93', 'param_1': 1}]\\n(Background on this error at: https://sqlalche.me/e/20/f405)", "operation": "update_iteration_result", "transaction_id": "job#a3fdea26-8d57-40bd-95cb-3b2b229b9f93"}	\N	\N	success	2026-08-04 20:25:41.824918	t
8	db_rollback	database_transaction	job#a3fdea26-8d57-40bd-95cb-3b2b229b9f93	\N	\N	{"error": "(psycopg2.errors.UndefinedColumn) column jobs.session_folder does not exist\\nLINE 1: ...d_time, jobs.log_file_path AS jobs_log_file_path, jobs.sessi...\\n                                                             ^\\n\\n[SQL: SELECT jobs.id AS jobs_id, jobs.job_id AS jobs_job_id, jobs.user_id AS jobs_user_id, jobs.device_id AS jobs_device_id, jobs.device_ip AS jobs_device_ip, jobs.device_name AS jobs_device_name, jobs.execution_queue AS jobs_execution_queue, jobs.methods AS jobs_methods, jobs.iterations AS jobs_iterations, jobs.sequence_id AS jobs_sequence_id, jobs.sequence_name AS jobs_sequence_name, jobs.execution_type AS jobs_execution_type, jobs.status AS jobs_status, jobs.execution_context_id AS jobs_execution_context_id, jobs.current_step AS jobs_current_step, jobs.current_iteration AS jobs_current_iteration, jobs.iteration_results AS jobs_iteration_results, jobs.start_time AS jobs_start_time, jobs.end_time AS jobs_end_time, jobs.log_file_path AS jobs_log_file_path, jobs.session_folder AS jobs_session_folder, jobs.team_name AS jobs_team_name, jobs.created_at AS jobs_created_at, jobs.updated_at AS jobs_updated_at \\nFROM jobs \\nWHERE jobs.job_id = %(job_id_1)s \\n LIMIT %(param_1)s]\\n[parameters: {'job_id_1': 'a3fdea26-8d57-40bd-95cb-3b2b229b9f93', 'param_1': 1}]\\n(Background on this error at: https://sqlalche.me/e/20/f405)", "operation": "update_job_status", "transaction_id": "job#a3fdea26-8d57-40bd-95cb-3b2b229b9f93"}	\N	\N	success	2026-08-04 20:25:42.501345	t
9	db_rollback	database_transaction	job_batch#batch_72_jobs	\N	\N	{"error": "(psycopg2.errors.UndefinedColumn) column jobs.session_folder does not exist\\nLINE 1: ...d_time, jobs.log_file_path AS jobs_log_file_path, jobs.sessi...\\n                                                             ^\\n\\n[SQL: SELECT jobs.id AS jobs_id, jobs.job_id AS jobs_job_id, jobs.user_id AS jobs_user_id, jobs.device_id AS jobs_device_id, jobs.device_ip AS jobs_device_ip, jobs.device_name AS jobs_device_name, jobs.execution_queue AS jobs_execution_queue, jobs.methods AS jobs_methods, jobs.iterations AS jobs_iterations, jobs.sequence_id AS jobs_sequence_id, jobs.sequence_name AS jobs_sequence_name, jobs.execution_type AS jobs_execution_type, jobs.status AS jobs_status, jobs.execution_context_id AS jobs_execution_context_id, jobs.current_step AS jobs_current_step, jobs.current_iteration AS jobs_current_iteration, jobs.iteration_results AS jobs_iteration_results, jobs.start_time AS jobs_start_time, jobs.end_time AS jobs_end_time, jobs.log_file_path AS jobs_log_file_path, jobs.session_folder AS jobs_session_folder, jobs.team_name AS jobs_team_name, jobs.created_at AS jobs_created_at, jobs.updated_at AS jobs_updated_at \\nFROM jobs \\nWHERE jobs.job_id = %(job_id_1)s \\n LIMIT %(param_1)s]\\n[parameters: {'job_id_1': 'b6f3ac60-5661-43d7-918b-4ecb2a0d2c8e', 'param_1': 1}]\\n(Background on this error at: https://sqlalche.me/e/20/f405)", "operation": "save_all_jobs", "transaction_id": "job_batch#batch_72_jobs"}	\N	\N	success	2026-08-08 17:43:15.831113	t
10	db_rollback	database_transaction	job_batch#batch_71_jobs	\N	\N	{"error": "(psycopg2.errors.UndefinedColumn) column jobs.session_folder does not exist\\nLINE 1: ...d_time, jobs.log_file_path AS jobs_log_file_path, jobs.sessi...\\n                                                             ^\\n\\n[SQL: SELECT jobs.id AS jobs_id, jobs.job_id AS jobs_job_id, jobs.user_id AS jobs_user_id, jobs.device_id AS jobs_device_id, jobs.device_ip AS jobs_device_ip, jobs.device_name AS jobs_device_name, jobs.execution_queue AS jobs_execution_queue, jobs.methods AS jobs_methods, jobs.iterations AS jobs_iterations, jobs.sequence_id AS jobs_sequence_id, jobs.sequence_name AS jobs_sequence_name, jobs.execution_type AS jobs_execution_type, jobs.status AS jobs_status, jobs.execution_context_id AS jobs_execution_context_id, jobs.current_step AS jobs_current_step, jobs.current_iteration AS jobs_current_iteration, jobs.iteration_results AS jobs_iteration_results, jobs.start_time AS jobs_start_time, jobs.end_time AS jobs_end_time, jobs.log_file_path AS jobs_log_file_path, jobs.session_folder AS jobs_session_folder, jobs.team_name AS jobs_team_name, jobs.created_at AS jobs_created_at, jobs.updated_at AS jobs_updated_at \\nFROM jobs \\nWHERE jobs.job_id = %(job_id_1)s \\n LIMIT %(param_1)s]\\n[parameters: {'job_id_1': 'b5cfd240-f4ea-4dd3-9225-dc21c90a3028', 'param_1': 1}]\\n(Background on this error at: https://sqlalche.me/e/20/f405)", "operation": "save_all_jobs", "transaction_id": "job_batch#batch_71_jobs"}	\N	\N	success	2026-08-08 17:45:20.075491	t
11	db_rollback	database_transaction	job_batch#batch_70_jobs	\N	\N	{"error": "(psycopg2.errors.UndefinedColumn) column jobs.session_folder does not exist\\nLINE 1: ...d_time, jobs.log_file_path AS jobs_log_file_path, jobs.sessi...\\n                                                             ^\\n\\n[SQL: SELECT jobs.id AS jobs_id, jobs.job_id AS jobs_job_id, jobs.user_id AS jobs_user_id, jobs.device_id AS jobs_device_id, jobs.device_ip AS jobs_device_ip, jobs.device_name AS jobs_device_name, jobs.execution_queue AS jobs_execution_queue, jobs.methods AS jobs_methods, jobs.iterations AS jobs_iterations, jobs.sequence_id AS jobs_sequence_id, jobs.sequence_name AS jobs_sequence_name, jobs.execution_type AS jobs_execution_type, jobs.status AS jobs_status, jobs.execution_context_id AS jobs_execution_context_id, jobs.current_step AS jobs_current_step, jobs.current_iteration AS jobs_current_iteration, jobs.iteration_results AS jobs_iteration_results, jobs.start_time AS jobs_start_time, jobs.end_time AS jobs_end_time, jobs.log_file_path AS jobs_log_file_path, jobs.session_folder AS jobs_session_folder, jobs.team_name AS jobs_team_name, jobs.created_at AS jobs_created_at, jobs.updated_at AS jobs_updated_at \\nFROM jobs \\nWHERE jobs.job_id = %(job_id_1)s \\n LIMIT %(param_1)s]\\n[parameters: {'job_id_1': 'ba023791-1465-466e-8409-fdd459eae734', 'param_1': 1}]\\n(Background on this error at: https://sqlalche.me/e/20/f405)", "operation": "save_all_jobs", "transaction_id": "job_batch#batch_70_jobs"}	\N	\N	success	2026-08-08 18:18:27.830173	t
\.


--
-- Data for Name: data_sync_log; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.data_sync_log (id, sync_id, source_location, source_instance, entity_type, entity_id, action_type, data_hash, conflict_detected, conflict_resolution, approved_by, github_sync_status, github_commit_sha, is_encrypted, "timestamp") FROM stdin;
\.


--
-- Data for Name: devices; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.devices (id, ip, name, username, password, port, device_type, mac_address, vnc_url, location, team_name, use_jump_host, jump_host_config, ir_config, created_by, created_at, updated_at, is_active) FROM stdin;
1	10.0.0.102	WestingHouse-4K-DESK	root		10022	XUMO	58:41:46:5C:E4:B4	http://10.0.0.101:5800/	US	LRQA	f	{}	{"ir_port": "2", "itach_ip": "10.0.0.142", "itach_port": 4998}	\N	2026-08-04 00:00:33.381354	2026-08-04 00:00:33.381376	t
2	10.0.0.233	SHARP-4K	root		10022	XUMO	58:41:46:C6:11:DE	http://10.0.0.232:5800/	US	LRQA	f	{}	{"ir_port": "3", "itach_ip": "10.0.0.30", "itach_port": 4998}	\N	2026-08-04 00:00:33.381354	2026-08-04 00:00:33.381376	t
3	10.0.0.95	CELLO-SKY	root		10022	SKY STREAM	FC:D2:90:00:09:AC	http://10.0.0.95:5800/	US	LRQA	f	{}	{"ir_port": "1", "itach_ip": "10.0.0.142", "itach_port": 4998}	\N	2026-08-04 00:00:33.381354	2026-08-04 00:00:33.381376	t
4	10.0.0.28	ELE_X3	root		10022	XUMO	A8:4A:63:00:D0:6B	http://10.0.0.28:5800/	US	LRQA	f	{}	{"ir_port": "1", "itach_ip": "10.0.0.30", "itach_port": 4998}	\N	2026-08-04 00:00:33.381354	2026-08-04 00:00:33.381376	t
5	10.0.0.61	ROGERS-WST-RTK-IUIv2	root		10022	XUMO	F4:6C:68:13:A2:5A	http://10.0.0.61:5800/	US	LRQA	f	{}	{"ir_port": "2", "itach_ip": "10.0.0.30", "itach_port": 4998}	\N	2026-08-04 00:00:33.381354	2026-08-04 00:00:33.381376	t
6	10.0.0.166	SKY-LLAMA-G2	root		10022	SKY STREAM	04:B8:6A:78:39:7B	http://10.0.0.166:5800/	US	LRQA	f	{}	{"ir_port": "2", "itach_ip": "10.0.0.142", "itach_port": 4998}	\N	2026-08-04 00:00:33.381354	2026-08-04 00:00:33.381376	t
7	10.0.0.230	SKY-XIONE-UK	root		10022	SKY STREAM	D4:52:EE:DC:EF:A3	http://10.0.0.230:5800/	US	LRQA	f	{}	{"ir_port": "1", "itach_ip": "10.0.0.30", "itach_port": 4998}	\N	2026-08-04 00:00:33.381354	2026-08-04 00:00:33.381376	t
8	10.0.0.148	SKY-XIONE-DE	root		10022	SKY STREAM	D4:52:EE:B7:3F:3E	http://10.0.0.148:5800/	US	LRQA	f	{}	{"ir_port": "2", "itach_ip": "10.0.0.142", "itach_port": 4998}	\N	2026-08-04 00:00:33.381354	2026-08-04 00:00:33.381376	t
9	10.0.0.250	ELEMENT_A4K	root		10022	XUMO	1C:2F:A2:30:35:B6	http://10.0.0.250:5800/	US	LRQA	f	{}	{"ir_port": "3", "itach_ip": "10.0.0.50", "itach_port": 4998}	\N	2026-08-04 00:00:33.381354	2026-08-04 00:00:33.381376	t
10	10.0.0.141	SKY_ALPACA_IT-141	root		10022	SKY STREAM	D4:DA:CD:FF:C5:50	http://10.0.0.141:5800/	US	LRQA	f	{}	{"ir_port": "2", "itach_ip": "10.0.0.30", "itach_port": 4998}	\N	2026-08-04 00:00:33.381354	2026-08-04 00:00:33.381376	t
11	10.0.0.252	SKY_ALPACA_IT-252	root		10022	SKY STREAM	D4:DA:CD:FF:AE:F4	http://10.0.0.252:5800/	US	LRQA	f	{}	{"ir_port": "1", "itach_ip": "10.0.0.30", "itach_port": 4998}	\N	2026-08-04 00:00:33.381354	2026-08-04 00:00:33.381376	t
12	10.0.0.75	SKY-UK-NEW	root		10022	SKY STREAM	D4:52:EE:D7:81:41	http://10.0.0.75:5800/	US	LRQA	f	{}	{}	\N	2026-08-04 00:00:33.381354	2026-08-04 00:00:33.381376	t
13	10.0.0.91	ROGERS-IUIv2-NEW	root		10022	XUMO	F4:6C:68:11:57:7A	http://10.0.0.91:5800/	US	LRQA	f	{}	{}	\N	2026-08-04 00:00:33.381354	2026-08-04 00:00:33.381376	t
14	10.0.0.156	BCM Rogers IUIv2	root		10022	XUMO	F0:46:3B:5B:F9:8D	http://10.0.0.156:5800/	US	LRQA	f	{}	{"ir_port": "1", "itach_ip": "10.0.0.30", "itach_port": 4998}	\N	2026-08-04 00:00:33.381354	2026-08-04 00:00:33.381376	t
15	10.0.0.140	DT_LAB_SKY_XIONE-UK	root		10022	SKY STREAM	04:B8:6A:16:0D:AB	http://10.0.0.140:5800/	US	LRQA	f	{}	{}	\N	2026-08-04 00:00:33.381354	2026-08-04 00:00:33.381376	t
\.


--
-- Data for Name: device_locks; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.device_locks (id, device_id, device_ip, user_id, job_id, lock_time, estimated_completion, eta_seconds, eta_formatted, is_active) FROM stdin;
\.


--
-- Data for Name: saved_sequences; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.saved_sequences (id, seq_id, name, description, methods, method_rationale, execution_count, total_duration_seconds, average_duration_seconds, team_name, location, created_by, created_at, updated_at, is_active) FROM stdin;
\.


--
-- Data for Name: jobs; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.jobs (id, job_id, user_id, device_id, device_ip, device_name, execution_queue, methods, iterations, sequence_id, sequence_name, execution_type, status, execution_context_id, current_step, current_iteration, iteration_results, start_time, end_time, log_file_path, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: execution_contexts; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.execution_contexts (id, job_id, device_snapshot, methods_snapshot, user_snapshot, environment_snapshot, system_config_snapshot, created_at) FROM stdin;
\.


--
-- Data for Name: implementation_progress; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.implementation_progress (id, requirement_id, requirement_name, status, progress_percentage, subtask_total, subtask_completed, phase_number, owner_user_id, target_completion_date, actual_completion_date, notes, updated_at) FROM stdin;
\.


--
-- Data for Name: ir_keycodes; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.ir_keycodes (id, keycode, description, button_name, category, device_type, created_at) FROM stdin;
\.


--
-- Data for Name: log_patterns; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.log_patterns (id, pattern_id, name, regex, description, team_name, location, is_custom, created_by, created_at, updated_at, is_active) FROM stdin;
\.


--
-- Data for Name: methods; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.methods (id, method_id, name, description, script_path, parameters, team_name, location, created_by, created_at, updated_at, is_active) FROM stdin;
\.


--
-- Data for Name: staging_changes; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.staging_changes (id, change_id, entity_type, entity_data, submitted_by, submitted_at, status, reviewed_by, review_comment, reviewed_at, approved_at) FROM stdin;
\.


--
-- Data for Name: system_commands; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.system_commands (id, cmd_id, name, command, description, category, team_name, location, is_custom, created_by, created_at, updated_at, is_active) FROM stdin;
\.


--
-- Data for Name: test_results; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.test_results (id, job_id, iteration, phase, status, details, device_id, device_name, device_ip, method, username, sequence_name, screenshots, logs, performance_seconds, optional_checks, build_info, tiles_summary, rdk_milestones_log, boot_type, execution_context_id, "timestamp", created_at) FROM stdin;
\.


--
-- Name: agent_status_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.agent_status_id_seq', 1, false);


--
-- Name: app_credentials_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.app_credentials_id_seq', 4, true);


--
-- Name: audit_logs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.audit_logs_id_seq', 11, true);


--
-- Name: data_sync_log_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.data_sync_log_id_seq', 1, false);


--
-- Name: device_locks_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.device_locks_id_seq', 1, false);


--
-- Name: devices_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.devices_id_seq', 15, true);


--
-- Name: execution_contexts_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.execution_contexts_id_seq', 1, false);


--
-- Name: implementation_progress_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.implementation_progress_id_seq', 1, false);


--
-- Name: ir_keycodes_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.ir_keycodes_id_seq', 1, false);


--
-- Name: jobs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.jobs_id_seq', 1, false);


--
-- Name: log_patterns_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.log_patterns_id_seq', 1, false);


--
-- Name: methods_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.methods_id_seq', 1, false);


--
-- Name: saved_sequences_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.saved_sequences_id_seq', 1, false);


--
-- Name: staging_changes_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.staging_changes_id_seq', 1, false);


--
-- Name: system_commands_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.system_commands_id_seq', 1, false);


--
-- Name: test_results_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.test_results_id_seq', 1, false);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.users_id_seq', 1, false);


--
-- PostgreSQL database dump complete
--

\unrestrict Kr6bX7S9a6DWEOfw5QYf4Wty2LXMruREvvT9jJKnASsyBYtX1fsS8P917QDi7G3

