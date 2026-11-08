$TTL 86400
@	IN	SOA	ns1.esandi.com. esandi.admin.com. (
			1		; Serial
			604800		; Refresh
			86400		; Retry
			2419200		; Expire
			86400 )		; Negative Cache TTL
;
@	IN	NS	ns1.esandi.com
@	IN	A	192.168.65.4
